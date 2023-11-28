# Denota Shield API
This API is designed to facilitate interaction with the Denota protocol. The API includes endpoints for the onboarding, transaction management, and recovery.

## Setup
Clone the repository and navigate to the project directory.

Create the virtual environment
```bash
python3 -m venv venv
```

Activate the virtual environment
```bash
source venv/bin/activate
```

Install the requirements
```bash
pip install -r requirements.txt
```

Create `.env` file and set the following flags: 
```bash
SUPABASE_URL=
SUPABASE_KEY=
PRIVATE_KEY=
```

Run the Flask application:

```bash
python app.py
```

The server should now be running at http://127.0.0.1:6000/. 

## Endpoints

### 1. Onboarding - `register`

- **Endpoint:** `/register`
- **Method:** `POST`

  **Input Parameters:**
  
  - `onrampName` (String): The name of the onramp being registered.
  - `coverageTier` (String): The tier of coverage desired for this onramp.
  - `historicalChargebackData` (JSON Array): A list of historical chargeback data for the onramp.

  **Output:**
  
  - `clientId` (String): The client ID used to authenticate API calls.
  - `clientSecret` (String): The client secret used to authenticate API calls.

### 2. Creating Nota - `nota`

- **Endpoint:** `/nota`
- **Method:** `POST`

  **Input Parameters:**
  
  - `paymentAmount` (Number): The amount of the transaction.
  - `paymentTime` (String): The time when the payment was made (in ISO 8601 format).
  - `withdrawalTime` (String): The time when the withdrawal was made (in ISO 8601 format).

  **Output:**
  
  - `notaId` (String): An identifier for the transaction.


### 3. Recovery - `recovery`

- **Endpoint:** `/recovery`
- **Method:** `POST`

  **Input Parameters:**
  
  - `notaId` (String): The identifier for the transaction.
  - `proofOfChargeback` (String): Encrypted proof of the chargeback.

  **Output:**
  
  - `claimId` (String): The identifier for the claim.

### 4. Recovery Status - `recovery`

- **Endpoint:** `/recovery`
- **Method:** `GET`

  **Input Parameters:**
  
  - `notaId` (String): The identifier for the transaction.

  **Output:**
  
  - `claimId` (String): The identifier for the claim.

  ## Next Steps
  Add API authentication system
  
  Integrate with blockchain through account abstraction
