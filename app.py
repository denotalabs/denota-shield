import json
from functools import wraps

import dotenv
from eth_abi import encode
from eth_account import Account
from flask import Flask, jsonify, request
from flask_cors import CORS
from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions
from web3 import Web3


def load_abi(file_name):
    with open(file_name, 'r') as abi_file:
        return json.load(abi_file)


def private_key_to_address(private_key: str):
    account = Account.from_key(private_key)
    return account.address


registrarABI = load_abi("CheqRegistrar.json")['abi']
coverageABI = load_abi("Coverage.json")['abi']
eventsABI = load_abi("Events.json")['abi']

env_path = ".env"
url: str = dotenv.get_key(dotenv_path=env_path, key_to_get='SUPABASE_URL')
key: str = dotenv.get_key(dotenv_path=env_path, key_to_get='SUPABASE_KEY')
master_private_key: str = dotenv.get_key(
    dotenv_path=env_path, key_to_get='PRIVATE_KEY')

master_address = private_key_to_address(master_private_key)

supabase_options = ClientOptions

supabase: Client = create_client(
    url, key, ClientOptions(auto_refresh_token=False))

COVERAGE_CONTRACT_ADDRESS = '0xE8958F60bf2e3fa00be499b3E1cBcd52fBf389b6'
REGISTRAR_CONTRACT_ADDRESS = '0x50d535af78A154a493d6ed466B363DDeBE4Ee88f'
USDC_TOKEN_ADDRESS = '0xc5B6c09dc6595Eb949739f7Cd6A8d542C2aabF4b'

RPC_URL = 'https://polygon-mumbai-bor.publicnode.com/'
w3 = Web3(Web3.HTTPProvider(RPC_URL))

erc20_abi = [
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

registrar = w3.eth.contract(
    address=REGISTRAR_CONTRACT_ADDRESS, abi=registrarABI)
coverage = w3.eth.contract(
    address=COVERAGE_CONTRACT_ADDRESS, abi=coverageABI)
usdc_contract = w3.eth.contract(
    address=USDC_TOKEN_ADDRESS, abi=erc20_abi)

app = Flask(__name__)
CORS(app)

# Onboarding endpoint


def send_transaction(tx, key):
    signed_tx = w3.eth.account.sign_transaction(tx, key)
    txn_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(txn_hash)
    return receipt


@app.route('/register', methods=['POST'])
def register_onramp():
    onramp_email = request.json.get('email')
    password = request.json.get('password')
    onramp_name = request.json.get('onrampName')
    coverage_tier = request.json.get('coverageTier')
    historical_chargeback_data = request.json.get('historicalChargebackData')
    invite_code = request.json.get('inviteCode')

    if not invite_code == 'PAYMENTS_R_BROKEN':
        return jsonify({"error": "Invalid invite code"}), 401

    # Input validation
    if not all([onramp_name, onramp_email, password, coverage_tier]):
        return jsonify({"error": "Required fields are missing"}), 400

    # This returns a dict with the user's id
    try:
        res = supabase.auth.sign_up(
            {"email": onramp_email, "password": password})

    except Exception as e:
        if "User already registered" in str(e):
            res = supabase.auth.sign_in_with_password(
                {"email": onramp_email, "password": password})
            users = supabase.table("User").select(
                "*").eq("id", str(res.user.id)).execute()
            user = users.data[0]
            private_key = user["private_key"]
            address = private_key_to_address(private_key)
            return jsonify({"address": address}), 304
        else:
            return "Registration error", 500

    if res is None:
        return jsonify({"error": "User already exists"}), 400

    if not res.user:
        return jsonify({"error": 500}), 500

    # generate user's web3 wallet then save it to the database
    private_key = setup_new_account()

    # add to user table
    user_data = {
        "id": res.user.id,
        "name": onramp_name,
        "coverage_tier": coverage_tier,
        "historical_chargeback_data": historical_chargeback_data,
        "private_key": private_key
    }

    res = supabase.table("User").insert(user_data).execute()

    address = private_key_to_address(private_key)

    if not res.data:
        return jsonify({"error": 500}), 500

    return jsonify({"address": address}), 200


def setup_new_account():
    # Create a new account
    new_account = w3.eth.account.create()
    nonce = w3.eth.get_transaction_count(
        private_key_to_address(master_private_key))

    # Send 0.01 Matic from master account to the new account
    tx = {
        'chainId': 80001,
        'to': new_account.address,
        'value': Web3.to_wei(0.05, 'ether'),
        'gas': 400000,
        'gasPrice': w3.to_wei('200', 'gwei'),
        'nonce': nonce,
    }
    send_transaction(tx, master_private_key)

    amount_wei = w3.to_wei(1000, 'ether')
    # Send USDC to address
    transfer_tx = usdc_contract.functions.transfer(new_account.address, amount_wei).build_transaction({
        'chainId': 80001,
        'gas': 400000,
        'gasPrice': w3.to_wei('200', 'gwei'),
        'nonce': w3.eth.get_transaction_count(master_address),
        'from': master_address
    })
    send_transaction(transfer_tx, master_private_key)

    new_account_key = new_account.key.hex()

    # Approve infinite spending on USDC token for the registrar contract
    infinite_approval_tx = usdc_contract.functions.approve(REGISTRAR_CONTRACT_ADDRESS, 2**256 - 1).build_transaction({
        'chainId': 80001,
        'gas': 400000,
        'gasPrice': w3.to_wei('100', 'gwei'),
        'nonce': w3.eth.get_transaction_count(new_account.address),
        'from': new_account.address
    })
    send_transaction(infinite_approval_tx, new_account_key)

    return new_account_key


def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        response = supabase.auth.get_user(token)
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
    res = supabase.auth.sign_in_with_password(
        {"email": onramp_email, "password": password})

    if not res.session:
        return jsonify({"error": 500}), 500

    return jsonify({"access_token": res.session.access_token, "refresh_token": res.session.refresh_token, "expires_in": res.session.expires_in}), 200


# Refresh token endpoint


@app.route('/token/refresh', methods=['POST'])
def refresh_token():
    refresh_token = request.json.get('refreshToken')

    # Validate the input
    if not refresh_token:
        return jsonify({"error": "Refresh token is missing!"}), 400

    # Use the refresh token to get a new access token
    res = supabase.auth.refresh_session(refresh_token)

    if not res.session:
        return jsonify({"error": "Invalid or expired refresh token!"}), 401

    # Return the new access token and its expiry time
    return jsonify({"access_token": res.session.access_token, "refresh_token": res.session.refresh_token, "expires_in": res.session.expires_in}), 200

# User endpoint


@app.route('/user', methods=['GET'])
@token_required
def get_user():
    res = supabase.auth.get_user(request.headers.get('Authorization'))
    user_id = res.user.id
    email = res.user.email

    users = supabase.table("User").select("*").eq("id", str(user_id)).execute()

    user = users.data[0]

    private_key = user["private_key"]
    address = private_key_to_address(private_key)

    return jsonify({"subaccount_address": address, "email": email}), 200


# Quote endpoint


@app.route('/quote', methods=['POST'])
@token_required
def get_quote():
    payment_amount = float(request.json.get('paymentAmount'))
    risk_score = float(request.json.get('riskScore'))

    quote = (payment_amount/10000.0)*risk_score

    return jsonify({"quote": quote}), 200

# Transactions endpoint


@app.route('/nota', methods=['POST'])
@token_required
def add_nota():
    # TODO This is a duplicated call for now (decorator and here)
    res = supabase.auth.get_user(request.headers.get('Authorization'))

    user_id = res.user.id
    payment_amount = float(request.json.get('paymentAmount'))
    risk_score = float(request.json.get('riskScore'))

    # Ensure the required parameters are provided
    if not all([user_id, payment_amount, risk_score]):
        return jsonify({"error": "Required parameters missing!"}), 400

    users = supabase.table("User").select("*").eq("id", str(user_id)).execute()

    user = users.data[0]

    # Mint nota NFT using web3 wallet
    private_key = user["private_key"]
    address = private_key_to_address(private_key)
    _, onchain_id = mint_onchain_nota(
        private_key, address, payment_amount, risk_score)

    if onchain_id is None:
        raise Exception("Nota creation failed")

    nota_data = {
        "user_id": user_id,
        "payment_amount": payment_amount,
        "risk_score": risk_score,
        "onchain_id": onchain_id,
        "recovery_status": 0  # 0 = not initiated, 1 = pending, 2 = completed
    }

    # Sanitize input (don't allow duplicate minting, etc.)
    res = supabase.table("Nota").insert(nota_data).execute()
    if not res.data:
        return jsonify({"error": 500}), 500

    notas = res.data
    if len(notas) > 1:
        raise Exception("More than one nota was created")

    nota_id = notas[0]["id"]
    if nota_id is None:
        return jsonify({"error": "Failed to create nota"}), 400

    # response.data["id"]
    return jsonify({"notaId": nota_id, "onchainId": onchain_id}), 200


def mint_onchain_nota(key, address, payment_amount, risk_score):
    payment_amount_wei = w3.to_wei(payment_amount, 'ether')
    risk_fee_wei = w3.to_wei((payment_amount_wei/10000.0)*risk_score, 'wei')

    payload = encode(["address", "uint256", "uint256"], [
                     address, payment_amount_wei, risk_score])
    transaction = registrar.functions.write(USDC_TOKEN_ADDRESS, 0, risk_fee_wei, COVERAGE_CONTRACT_ADDRESS, COVERAGE_CONTRACT_ADDRESS, payload).build_transaction({
        'chainId': 80001,  # For mainnet
        'gas': 400000,  # Estimated gas, change accordingly
        'gasPrice': w3.to_wei('100', 'gwei'),
        'nonce': w3.eth.get_transaction_count(address)
    })
    receipt = send_transaction(transaction, key)
    nota_id = nota_id_from_log(receipt)

    return receipt['transactionHash'].hex(), nota_id


def nota_id_from_log(receipt):
    # Create a contract "object" only for parsing logs (no address needed as we're not interacting with the contract itself)
    contract = w3.eth.contract(abi=eventsABI)

    # Parse logs
    parsed_logs = []
    for log in receipt['logs']:
        try:
            parsed_log = contract.events.Written().process_log(log)
            parsed_logs.append(parsed_log)
        except:
            pass

    # Filter logs for event with the name "Written"
    written_logs = [log for log in parsed_logs if log['event'] == 'Written']

    id = written_logs[0]['args']['cheqId'] if written_logs else None

    return str(id) if id else None

# Get Notas


@app.route('/notas', methods=['GET'])
@token_required
def get_notas_for_user():
    # Retrieve the user from the token
    res = supabase.auth.get_user(request.headers.get('Authorization'))
    user_id = res.user.id

    # Query the 'Nota' table using the user_id
    notas = supabase.table("Nota").select(
        "*").eq("user_id", str(user_id)).execute()

    # Check if the query returned any notas
    if not notas:
        return jsonify({"error": "No notas found for the user"}), 404

    # Return the list of notas
    return jsonify(notas.data)

# Recovery endpoint


@app.route('/recovery', methods=['POST'])
@token_required
def initiate_recovery():
    user = supabase.auth.get_user(request.headers.get('Authorization'))

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

    nota = notas.data

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
    transaction = coverage.functions.recoverFunds(nota_id).build_transaction({
        'chainId': 80001,  # For mainnet
        'gas': 400000,  # Estimated gas, change accordingly
        'gasPrice': w3.to_wei('200', 'gwei'),
        'nonce': w3.eth.get_transaction_count(address)
    })
    receipt = send_transaction(transaction, key)

    return receipt['transactionHash'].hex()

# Recovery status endpoint


@app.route('/recovery/<int:nota_id>', methods=['GET'])
@token_required
def get_recovery(nota_id):
    user = supabase.auth.get_user(request.headers.get('Authorization'))
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
    app.run(debug=True, port=6000)
