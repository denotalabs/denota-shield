from flask import Flask, jsonify, request

app = Flask(__name__)

# Onboarding endpoint


@app.route('/registerOnramp', methods=['POST'])
def register_onramp():
    onramp_name = request.json.get('onrampName')
    coverage_tier = request.json.get('coverageTier')
    historical_chargeback_data = request.json.get('historicalChargebackData')

    # TODO: Onboard the onramp and return credentials

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
    app.run(debug=True)
