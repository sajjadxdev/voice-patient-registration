# Telephony & Real Phone Number Provisioning Guide

This guide explains how to connect a real, dialable U.S. phone number to the Oakwood Health Voice AI intake system using **Vapi**, **Twilio**, or **Local ngrok Tunneling**, as well as the **Browser Voice Simulator**.

---

## Option 1: Vapi Integration (Fastest & Recommended)

Vapi provides built-in telephony, ultra-low latency Deepgram speech-to-text, and ElevenLabs voice synthesis.

### Step 1: Provision a Phone Number in Vapi
1. Go to the [Vapi Dashboard](https://dashboard.vapi.ai) and sign in.
2. Navigate to **Phone Numbers** in the left menu.
3. Click **Buy Number** or **Import Twilio Number**, select any U.S. area code, and click Purchase ($1.50/mo or free trial credits).

### Step 2: Create Assistant
1. In the Vapi Dashboard, go to **Assistants** -> **Create Assistant**.
2. Select **Custom Assistant** or import `docs/vapi_assistant_spec.json`.
3. Set **Model** to `gpt-4o-mini`.
4. Under **Server URL**, paste your live webhook URL:
   ```
   https://<YOUR-APP-DOMAIN>.railway.app/voice/vapi/webhook
   ```
   *(If testing locally with ngrok: `https://<YOUR-NGROK-SUBDOMAIN>.ngrok-free.app/voice/vapi/webhook`)*

### Step 3: Attach Phone Number to Assistant
1. Go back to **Phone Numbers**, select your provisioned number, and choose your assistant in the **Assistant** dropdown.
2. Click **Save**.

### Step 4: Dial and Test
Dial your provisioned U.S. number from your cell phone! Sarah will greet you, collect your demographics, confirm your details, write to the persistent SQLite database, and offer an appointment.

---

## Option 2: Twilio Voice Integration

If you prefer using Twilio directly with our built-in TwiML Gather engine:

### Step 1: Provision a Phone Number in Twilio
1. Sign in to the [Twilio Console](https://console.twilio.com).
2. Go to **Phone Numbers** -> **Manage** -> **Active numbers** -> **Buy a number**.
3. Choose a U.S. number with **Voice** capabilities.

### Step 2: Configure Inbound Voice Webhook
1. Click on your active phone number.
2. Scroll to the **Voice Configuration** section:
   - **A Call Comes In**: Select `Webhook`.
   - **URL**: `https://<YOUR-APP-DOMAIN>/voice/twilio/incoming`
   - **HTTP Method**: `POST`
3. Click **Save Configuration**.

### Step 3: Dial and Test
Call your Twilio phone number. Twilio's neural voice will speak the greeting, transcribe your responses in real time, and persist records to the API.

---

## Option 3: Local Development with ngrok

To expose your local development server to Vapi or Twilio:

```bash
# Terminal 1: Run the backend application
python run.py

# Terminal 2: Expose port 8000 via ngrok
ngrok http 8000
```

Copy the public HTTPS URL from ngrok (e.g., `https://a1b2c3d4.ngrok-free.app`) and use:
- Vapi Server URL: `https://a1b2c3d4.ngrok-free.app/voice/vapi/webhook`
- Twilio Webhook: `https://a1b2c3d4.ngrok-free.app/voice/twilio/incoming`

---

## Option 4: Browser Voice Call Simulator (No Telecom Account Needed)

If carrier verification, vendor credits, or telephony provisioning is delayed, you can test the **exact same end-to-end voice flow** inside your browser:

1. Start the server:
   ```bash
   python run.py
   ```
2. Open [http://localhost:8000/dashboard](http://localhost:8000/dashboard) in Google Chrome, Edge, or Safari.
3. Click **"Click to Speak (Microphone)"** to speak naturally into your mic.
4. Sarah will speak back to you with audio synthesis, execute tool validations, check for duplicates, and save the patient to the live database!
