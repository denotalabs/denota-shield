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
    
    session = supabase.auth.sign_in(onramp_email, password) # This returns a dict with the user's id
    status_code = session.get("status_code")
    if (status_code != 200) and (status_code != 201):
        return jsonify({"error": status_code}), status_code
    
    return session.get("access_token"), status_code

# Transactions endpoint
@app.route('/nota', methods=['POST'])
@token_required
def add_nota():
    res = supabase.auth.api.get_user(request.headers.get('Authorization')) # TODO This is a duplicated call for now (decorator and here)
    
    user_id = res.get("id")
    payment_amount = request.json.get('paymentAmount')
    risk_score = request.json.get('riskScore')
    
    # Ensure the required parameters are provided
    if not all([user_id, payment_amount, risk_score]):
        return jsonify({"error": "Required parameters missing!"}), 400
    
    # TODO: Mint nota NFT using web3 wallet
    
    nota_data = {
        "user_id": user_id,
        "payment_amount": payment_amount,
        "risk_score": risk_score,
        "recovery_status": 0 # 0 = not initiated, 1 = pending, 2 = completed
    }
    
    res = supabase.table("Nota").insert(nota_data).execute() # Sanitize input (don't allow duplicate minting, etc.)
    status_code = res.get("status_code")
    if (status_code != 200) and (status_code != 201):
        return jsonify({"error": status_code}), status_code
    
    notas = res.get("data")
    if len(notas) > 1:
        raise Exception("More than one nota was created")
    
    nota_id = notas[0].get("id")
    if nota_id is None:
        return jsonify({"error": "Failed to create nota"}), 400

    return jsonify({"notaId": nota_id}), status_code #response.data["id"]


# Recovery endpoint
@app.route('/recovery', methods=['POST'])
@token_required
def initiate_recovery():
    user = supabase.auth.api.get_user(request.headers.get('Authorization'))
    
    user_id = user["id"]
    nota_id = request.json.get('notaId')

    notas = supabase.table("Nota").select("*").eq("id", str(nota_id)).eq("user_id", str(user_id)).execute() # Limit 1?
    if notas is None:
        return jsonify({"error": "Doesn't exist or not authorized"}), 400
    
    nota = notas.get("data")

    if len(nota) > 1:
        raise Exception("More than one nota was created")
    nota = nota[0]

    proof_of_chargeback = request.json.get('proofOfChargeback')
    old_nota = supabase.table("Nota").select("*").eq("id", str(nota_id)).execute()
    old_nota = old_nota.get("data")[0]

    old_nota["proof_of_chargeback"] = proof_of_chargeback
    old_nota["recovery_status"] = 1

    res = supabase.table("Nota").update(old_nota).eq("id", str(nota_id)).execute()
    
    status_code = res.get("status_code")
    if (status_code != 200) and (status_code != 201):
        return jsonify({"error": status_code}), status_code

    return jsonify({"message": "success"}), status_code # TODO What should this return?

# Recovery status endpoint
@app.route('/recovery/<int:nota_id>', methods=['GET'])
@token_required
def get_recovery(nota_id):
    user = supabase.auth.api.get_user(request.headers.get('Authorization'))
    user_id = user["id"]
    
    nota = supabase.table("Nota").select("*").eq("id", str(nota_id)).eq("user_id", user_id).execute()
    if not nota:
        return jsonify({"error": "Doesn't exist or not authorized"}), 400
    
    return jsonify({"status": nota.data[0]["recovery_status"]})


if __name__ == "__main__":
    app.run(debug=True, port=3000)


