from flask import Flask, jsonify, request
from supabase_py import create_client, Client

SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_ANON_KEY = "YOUR_SUPABASE_ANON_KEY"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
app = Flask(__name__)

# TODO Set up database for (Onramp, Nota)
# TODO Set up AA wallet for each onramp (API-> register+creation, API-> Nota minting, API-> Nota recovery)
# Having the claim process rely on us managing the wallet and giving them access?

class Onramp:
    def __init__(self, name, coverage_tier, historical_chargeback_data):
        self.name = name
        self.coverage_tier = coverage_tier
        self.historical_chargeback_data = historical_chargeback_data

    def __repr__(self):
        return f'<Onramp {self.name}>'  

class Nota:
    def __init__(self, nota_id, onramp, payment_amount, payment_time, withdrawal_time):
        self.nota_id = nota_id
        self.onramp = onramp
        self.payment_amount = payment_amount
        self.payment_time = payment_time

    def __repr__(self):
        return f'<Nota {self.nota_id}>'

# Onboarding endpoint
@app.route('/register', methods=['POST'])
def register_onramp():
    onramp_name = request.json.get('onrampName')
    coverage_tier = request.json.get('coverageTier')

    # TODO need to store this somewhere. Also update it with onchain data
    # Question: Will onramps share their historical data?
    historical_chargeback_data = request.json.get('historicalChargebackData')

    # TODO: Onboard the onramp and return credentials
    onramp = Onramp(name=onramp_name, coverage_tier=coverage_tier, historical_chargeback_data=historical_chargeback_data)
    data, count = supabase.table('onramp').insert({"id": 1, "name": "Denmark"}).execute()

    # For now, returning a stubbed response
    return jsonify({
        "clientId": "stubbed_client_id",
        "clientSecret": "stubbed_client_secret"
    })

# Transactions endpoint
@app.route('/addTransaction', methods=['POST'])
def add_transaction():
    payment_amount = request.json.get('paymentAmount')
    payment_time = request.json.get('paymentTime')
    withdrawal_time = request.json.get('withdrawalTime')

    # TODO: Mint nota NFT

    # For now, returning a stubbed response
    return jsonify({
        "notaId": "stubbed_nota_id"
    })

# Recovery endpoint
@app.route('/initiateRecovery', methods=['POST'])
def initiate_recovery():
    nota_id = request.json.get('notaId')
    proof_of_chargeback = request.json.get('proofOfChargeback')

    # TODO: Process the recovery request
    # For now, returning a stubbed response
    return jsonify({
        "claimId": "stubbed_claim_id"
    })


if __name__ == "__main__":
    app.run(debug=True) # changing to 0.0.0 port opens it to the outside
