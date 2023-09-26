from functools import wraps

import dotenv
from eth_account import Account
from flask import Flask, jsonify, request
from supabase_py import Client, create_client
from web3 import Web3

env_path = ".env"
url: str = dotenv.get_key(dotenv_path=env_path, key_to_get='SUPABASE_URL')
key: str = dotenv.get_key(dotenv_path=env_path, key_to_get='SUPABASE_KEY')
supabase: Client = create_client(url, key)

INFURA_URL = 'https://polygon-mumbai-bor.publicnode.com/'
w3 = Web3(Web3.HTTPProvider(INFURA_URL))
registrar = w3.eth.contract(address="", abi={})
coverage = w3.eth.contract(address="", abi={})


app = Flask(__name__)

# Onboarding endpoint


def private_key_to_address(private_key: str):
    return Web3.toChecksumAddress(Web3.eth.account.privateKeyToAccount(private_key).address)


@app.route('/register', methods=['POST'])
def register_onramp():
    onramp_email = request.json.get('email')
    password = request.json.get('password')
    onramp_name = request.json.get('onrampName')
    coverage_tier = request.json.get('coverageTier')
    historical_chargeback_data = request.json.get('historicalChargebackData')

    # Input validation
    if not all([onramp_name, onramp_email, password, coverage_tier]):
        return jsonify({"error": "Required fields are missing"}), 400

    # This returns a dict with the user's id
    res = supabase.auth.sign_up(onramp_email, password)
    if res is None:
        return jsonify({"error": "User already exists"}), 400
    status_code = res.get("status_code")
    if (status_code != 200) and (status_code != 201):
        return jsonify({"error": status_code}), status_code

    # generate user's web3 wallet then save it to the database
    new_account = Account.create()
    private_key = new_account.privateKey.hex()

    # add to user table
    user_data = {
        "id": res.get("id"),
        "name": onramp_name,
        "coverage_tier": coverage_tier,
        "historical_chargeback_data": historical_chargeback_data,
        "private_key": private_key
    }

    res = supabase.table("User").insert(user_data).execute()
    status_code = res.get("status_code")
    if (status_code != 200) and (status_code != 201):
        return jsonify({"error": status_code}), status_code

    return f"Registration successful: {status_code}", status_code


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        response = supabase.auth.api.get_user(token)
        if 'error' in response:
            return jsonify({"error": "Invalid or expired token!"}), 401

        return f(*args, **kwargs)

    return decorated_function


# Onboarding endpoint
@app.route('/signin', methods=['POST'])
def onramp_signin():
    onramp_email = request.json.get('email')
    password = request.json.get('password')

    # Input validation
    if not all([onramp_email, password]):
        return jsonify({"error": "Required fields are missing"}), 400

    # This returns a dict with the user's id
    session = supabase.auth.sign_in(onramp_email, password)
    status_code = session.get("status_code")
    if (status_code != 200) and (status_code != 201):
        return jsonify({"error": status_code}), status_code

    return session.get("access_token"), status_code

# Transactions endpoint


@app.route('/nota', methods=['POST'])
@token_required
def add_nota():
    # TODO This is a duplicated call for now (decorator and here)
    res = supabase.auth.api.get_user(request.headers.get('Authorization'))

    user_id = res.get("id")
    payment_amount = request.json.get('paymentAmount')
    risk_score = request.json.get('riskScore')

    # Ensure the required parameters are provided
    if not all([user_id, payment_amount, risk_score]):
        return jsonify({"error": "Required parameters missing!"}), 400

    # Mint nota NFT using web3 wallet
    private_key = res.get("private_key")
    mint_onchain_nota(private_key, private_key_to_address(
        private_key), payment_amount, risk_score)

    nota_data = {
        "user_id": user_id,
        "payment_amount": payment_amount,
        "risk_score": risk_score,
        "recovery_status": 0  # 0 = not initiated, 1 = pending, 2 = completed
    }

    # Sanitize input (don't allow duplicate minting, etc.)
    res = supabase.table("Nota").insert(nota_data).execute()
    status_code = res.get("status_code")
    if (status_code != 200) and (status_code != 201):
        return jsonify({"error": status_code}), status_code

    notas = res.get("data")
    if len(notas) > 1:
        raise Exception("More than one nota was created")

    nota_id = notas[0].get("id")
    if nota_id is None:
        return jsonify({"error": "Failed to create nota"}), 400

    return jsonify({"notaId": nota_id}), status_code  # response.data["id"]


def mint_onchain_nota(key, address, payment_amount, risk_score):
    risk_fee = (payment_amount/10000)*risk_score
    payload = w3.eth.encodeABI(
        ["address", "uint256", "unit256"], ["", 1000, 50])
    transaction = registrar.functions.mint("token", 0, risk_fee, "coverageModule", "coverageModule", payload).buildTransaction({
        'chainId': 80001,  # For mainnet
        'gas': 2000000,  # Estimated gas, change accordingly
        'gasPrice': w3.toWei('200', 'gwei'),
        'nonce': w3.eth.getTransactionCount(address)
    })
    # Sign the transaction
    signed_txn = w3.eth.account.signTransaction(transaction, key)

    # Send the transaction
    txn_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)

    # Wait for the transaction receipt
    receipt = w3.eth.waitForTransactionReceipt(txn_hash)

    return receipt['transactionHash'].hex()


# Recovery endpoint
@app.route('/recovery', methods=['POST'])
@token_required
def initiate_recovery():
    user = supabase.auth.api.get_user(request.headers.get('Authorization'))

    user_id = user["id"]
    private_key = user["private_key"]
    nota_id = request.json.get('notaId')

    # Initiate recovery onchain
    tx_hash = initiate_onchain_recovery(
        private_key, private_key_to_address(private_key), nota_id)

    notas = supabase.table("Nota").select(
        "*").eq("id", str(nota_id)).eq("user_id", str(user_id)).execute()  # Limit 1?
    if notas is None:
        return jsonify({"error": "Doesn't exist or not authorized"}), 400

    nota = notas.get("data")

    if len(nota) > 1:
        raise Exception("More than one nota was created")
    nota = nota[0]

    proof_of_chargeback = request.json.get('proofOfChargeback')
    nota["proof_of_chargeback"] = proof_of_chargeback
    nota["recovery_status"] = 1

    res = supabase.table("Nota").insert(nota, upsert=True).execute()

    status_code = res.get("status_code")
    if (status_code != 200) and (status_code != 201):
        return jsonify({"error": status_code}), status_code

    return jsonify({"message": "success", "hash": tx_hash}), status_code


def initiate_onchain_recovery(key, address, nota_id):
    transaction = coverage.functions.recoverFunds(nota_id).buildTransaction({
        'chainId': 80001,  # For mainnet
        'gas': 2000000,  # Estimated gas, change accordingly
        'gasPrice': w3.toWei('200', 'gwei'),
        'nonce': w3.eth.getTransactionCount(address)
    })
    # Sign the transaction
    signed_txn = w3.eth.account.signTransaction(transaction, key)

    # Send the transaction
    txn_hash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)

    # Wait for the transaction receipt
    receipt = w3.eth.waitForTransactionReceipt(txn_hash)

    return receipt['transactionHash'].hex()

# Recovery status endpoint


@app.route('/recovery/<int:nota_id>', methods=['GET'])
@token_required
def get_recovery(nota_id):
    user = supabase.auth.api.get_user(request.headers.get('Authorization'))
    user_id = user["id"]

    notas = supabase.table("Nota").select(
        "*").eq("id", str(nota_id)).eq("user_id", str(user_id)).execute()  # Limit 1?
    if notas is None:
        return jsonify({"error": "Doesn't exist or not authorized"}), 400

    nota = notas.get("data")
    if len(nota) > 1:
        raise Exception("More than one nota was created")
    nota = nota[0]

    return jsonify({"status": nota["recovery_status"]})


if __name__ == "__main__":
    app.run(debug=True, port=3000)
