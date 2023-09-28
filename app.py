import json
from functools import wraps

import dotenv
from eth_account import Account
from flask import Flask, jsonify, request
from supabase import Client, create_client
from web3 import Web3


def load_abi(file_name):
    with open(file_name, 'r') as abi_file:
        return json.load(abi_file)


registrarABI = load_abi("CheqRegistrar.json")['abi']
coverageABI = load_abi("Coverage.json")['abi']
eventsABI = load_abi("Events.json")['abi']

env_path = ".env"
url: str = dotenv.get_key(dotenv_path=env_path, key_to_get='SUPABASE_URL')
key: str = dotenv.get_key(dotenv_path=env_path, key_to_get='SUPABASE_KEY')
master_private_key: str = dotenv.get_key(
    dotenv_path=env_path, key_to_get='PRIVATE_KEY')
supabase: Client = create_client(url, key)

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

# Onboarding endpoint


def private_key_to_address(private_key: str):
    account = Account.from_key(private_key)
    return account.address


def send_transaction(tx, key):
    signed_tx = w3.eth.account.sign_transaction(tx, key)
    txn_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(txn_hash)
    return receipt


@app.route('/register', methods=['POST'])
def register_onramp():
    # TODO: require an invite code to register

    onramp_email = request.json.get('email')
    password = request.json.get('password')
    onramp_name = request.json.get('onrampName')
    coverage_tier = request.json.get('coverageTier')
    historical_chargeback_data = request.json.get('historicalChargebackData')

    # Input validation
    if not all([onramp_name, onramp_email, password, coverage_tier]):
        return jsonify({"error": "Required fields are missing"}), 400

    # This returns a dict with the user's id
    res = supabase.auth.sign_up({"email": onramp_email, "password": password})

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

    if not res.data:
        return jsonify({"error": 500}), 500

    return f"Registration successful: 200", 200


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

    master_address = private_key_to_address(master_private_key)

    # Send USDC to address
    transfer_tx = usdc_contract.functions.transfer(new_account.address, 1000).build_transaction({
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

    return res.session.access_token, 200

# Transactions endpoint


@app.route('/nota', methods=['POST'])
@token_required
def add_nota():
    # TODO This is a duplicated call for now (decorator and here)
    res = supabase.auth.get_user(request.headers.get('Authorization'))

    user_id = res.user.id
    payment_amount = request.json.get('paymentAmount')
    risk_score = request.json.get('riskScore')

    # Ensure the required parameters are provided
    if not all([user_id, payment_amount, risk_score]):
        return jsonify({"error": "Required parameters missing!"}), 400

    users = supabase.table("User").select("*").eq("id", str(user_id)).execute()

    user = users.data[0]

    # Mint nota NFT using web3 wallet
    private_key = user["private_key"]
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
        ["address", "uint256", "unit256"], [address, 1000, 50])
    transaction = registrar.functions.mint(USDC_TOKEN_ADDRESS, 0, risk_fee, "coverageModule", "coverageModule", payload).build_transaction({
        'chainId': 80001,  # For mainnet
        'gas': 400000,  # Estimated gas, change accordingly
        'gasPrice': w3.toWei('100', 'gwei'),
        'nonce': w3.eth.getTransactionCount(address)
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

    # Assuming the desired ID is the second argument of the "Written" event
    id = written_logs[0]['args'][1] if written_logs else None

    return str(id) if id else None

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
    app.run(debug=True, port=3000)
