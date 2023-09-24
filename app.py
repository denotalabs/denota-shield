from flask import Flask, jsonify, request
from supabase_py import create_client, Client
from functools import wraps
import dotenv


env_path = ".env"
url: str = dotenv.get_key(dotenv_path=env_path, key_to_get='SUPABASE_URL')
key: str = dotenv.get_key(dotenv_path=env_path, key_to_get='SUPABASE_KEY')
supabase: Client = create_client(url, key)

app = Flask(__name__)

# Onboarding endpoint
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
    
    res = supabase.auth.sign_up(onramp_email, password) # This returns a dict with the user's id
    if res is None:
        return jsonify({"error": "User already exists"}), 400
    status_code = res.get("status_code")
    if (status_code != 200) and (status_code != 201):
        return jsonify({"error": status_code}), status_code
    
    # TODO generate user's web3 wallet then save it to the database

    # add to user table
    user_data = {
        "id": res.get("id"),
        "name": onramp_name,
        "coverage_tier": coverage_tier,
        "historical_chargeback_data": historical_chargeback_data
    }
    response = supabase.table("User").insert(user_data).execute() # TODO ensure that this succeeds before continuing

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
    
    session = supabase.auth.sign_in(onramp_email, password) # This returns a dict with the user's id
    status_code = session.get("status_code")
    if (status_code != 200) and (status_code != 201):
        return jsonify({"error": status_code}), status_code
    
    return session.get("access_token"), status_code

# Transactions endpoint
@app.route('/nota', methods=['POST'])
@token_required
def add_nota():
    payment_amount = request.json.get('paymentAmount')
    payment_time = request.json.get('paymentTime')
    withdrawal_time = request.json.get('withdrawalTime')

    # TODO: Mint nota NFT

    # For now, returning a stubbed response
    return jsonify({
        "notaId": "stubbed_nota_id"
    })

# Recovery endpoint
@app.route('/recovery', methods=['POST'])
@token_required
def initiate_recovery():
    nota_id = request.json.get('notaId')
    proof_of_chargeback = request.json.get('proofOfChargeback')

    # TODO: Process the recovery request
    # For now, returning a stubbed response
    return jsonify({
        "claimId": "stubbed_claim_id"
    })

# Recovery status endpoint
@app.route('/recovery/<int:nota_id>', methods=['GET'])
@token_required
def get_recovery(nota_id):
    # TODO: pull the nota status
    return jsonify({
        "claimId": "stubbed_claim_id"
    })


if __name__ == "__main__":
    app.run(debug=True, port=3000)
