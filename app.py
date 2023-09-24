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
    onramp_email = request.json.get('onrampName')
    password = request.json.get('password')
    coverage_tier = request.json.get('coverageTier')
    historical_chargeback_data = request.json.get('historicalChargebackData')

    res = supabase.auth.sign_up({"email": onramp_email, "password": password, "options": { "data": {"coverage_tier": coverage_tier, "historical_chargeback_data": historical_chargeback_data}}})

    if res.error:
        return jsonify({"error": res.error.message}), 400
    return jsonify({"message": "User created successfully!"}), 201

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
