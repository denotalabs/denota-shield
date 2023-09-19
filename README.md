# Denota Shield API
This API is designed to facilitate the onboarding of partners, management of transactions, and initiation of recovery processes for Denota.

## Setup
Ensure you have Python and Flask installed.
Clone the repository.
Navigate to the project directory and run the Flask application:

```bash
$ python app.py
```

The server should now be running at http://127.0.0.1:5000/. 

## Endpoints

### 1. Onboarding - `registerOnramp`

- **Endpoint:** `/registerOnramp`
- **Method:** `POST`

  **Input Parameters:**
  
  - `onrampName` (String): The name of the onramp being registered.
  - `coverageTier` (String): The tier of coverage desired for this onramp.
  - `historicalChargebackData` (JSON Array): A list of historical chargeback data for the onramp.

  **Output:**
  
  - `clientId` (String): The client ID used to authenticate API calls.
  - `clientSecret` (String): The client secret used to authenticate API calls.

### 2. Transactions - `addTransaction`

- **Endpoint:** `/addTransaction`
- **Method:** `POST`

  **Input Parameters:**
  
  - `paymentAmount` (Number): The amount of the transaction.
  - `paymentTime` (String): The time when the payment was made (in ISO 8601 format).
  - `withdrawalTime` (String): The time when the withdrawal was made (in ISO 8601 format).

  **Output:**
  
  - `notaId` (String): An identifier for the transaction.

### 3. Recovery - `initiateRecovery`

- **Endpoint:** `/initiateRecovery`
- **Method:** `POST`

  **Input Parameters:**
  
  - `notaId` (String): The identifier for the transaction.
  - `proofOfChargeback` (String): Encrypted proof of the chargeback.

  **Output:**
  
  - `claimId` (String): The identifier for the claim.
