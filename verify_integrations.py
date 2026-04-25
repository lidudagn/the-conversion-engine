import os
import asyncio
from dotenv import load_dotenv

# Load env variables from .env
load_dotenv()

import config
from agent.email_handler import EmailHandler
from agent.sms_handler import SMSHandler
from agent.hubspot_client import HubSpotClient
from agent.calendar_client import CalComClient
from agent.langfuse_wrapper import get_langfuse, create_trace, flush

async def verify_integrations():
    print("--- Starting Production Stack Verification ---")
    
    # 1. Resend (Email)
    print("\n1. Verifying Resend...")
    try:
        email_handler = EmailHandler()
        if not email_handler._client:
            print("❌ Resend client failed to initialize (check API key)")
        else:
            # We don't want to actually send an email if kill switch is off, but kill_switch should be ON by default
            print(f"✅ Resend client initialized. Kill switch: {config.KILL_SWITCH}")
            result = email_handler.send_email(
                to_email="test@example.com",
                subject="API Verification Test",
                body="This is a test from the verification script."
            )
            print(f"Result: {result['status']}")
            if result['status'] == 'sent':
                 print(f"✅ Resend successfully sent email (ID: {result.get('resend_id')})")
            elif result['status'] == 'error':
                 print(f"❌ Resend error: {result.get('error')}")
    except Exception as e:
        print(f"❌ Resend exception: {e}")

    # 2. Africa's Talking (SMS)
    print("\n2. Verifying Africa's Talking...")
    try:
        sms_handler = SMSHandler()
        if not sms_handler._client:
            print("❌ AT client failed to initialize (check API key)")
        else:
            print(f"✅ AT client initialized. Kill switch: {config.KILL_SWITCH}")
            result = sms_handler.send_sms(
                to_number="+251900000000",
                message="API Verification Test"
            )
            print(f"Result: {result['status']}")
            if result['status'] in ('sent', 'at_sandbox_queued'):
                 print("✅ AT successfully queued/sent SMS")
            elif result['status'] == 'error':
                 print(f"❌ AT error: {result.get('error')}")
    except Exception as e:
        print(f"❌ AT exception: {e}")

    # 3. HubSpot (CRM)
    print("\n3. Verifying HubSpot...")
    try:
        hubspot = HubSpotClient()
        if not hubspot._client:
            print("❌ HubSpot client failed to initialize (check Access Token)")
        else:
            print("✅ HubSpot client initialized.")
            hubspot.ensure_custom_properties()
            result = hubspot.create_or_update_contact(
                email="test_api_verifier@tenacious-test.com",
                first_name="API",
                last_name="Verifier",
                company="Tenacious Verification Data"
            )
            print(f"Result: {result['status']}")
            if result['status'] in ('created', 'updated'):
                 print(f"✅ HubSpot successfully created/updated contact (ID: {result.get('id')})")
            elif result['status'] == 'error':
                 print(f"❌ HubSpot error: {result.get('error')}")
    except Exception as e:
        print(f"❌ HubSpot exception: {e}")

    # 4. Cal.com
    print("\n4. Verifying Cal.com...")
    try:
        cal = CalComClient()
        if not cal._active:
            print("❌ Cal.com client is not active (mock mode). Check API key.")
        else:
            print("✅ Cal.com client initialized.")
            slots = await cal.get_available_slots()
            if slots:
                print(f"✅ Cal.com successfully fetched {len(slots)} available slots")
            else:
                print("⚠️ Cal.com fetched 0 slots, but API might be working")
    except Exception as e:
        print(f"❌ Cal.com exception: {e}")

    # 5. Langfuse
    print("\n5. Verifying Langfuse...")
    try:
        lf = get_langfuse()
        if not lf:
            print("❌ Langfuse client failed to initialize")
        else:
            print("✅ Langfuse client initialized.")
            trace = create_trace(name="api_verification_test")
            if trace:
                print("✅ Langfuse trace created successfully")
                flush()
            else:
                print("❌ Langfuse failed to create trace")
    except Exception as e:
        print(f"❌ Langfuse exception: {e}")

if __name__ == '__main__':
    asyncio.run(verify_integrations())
