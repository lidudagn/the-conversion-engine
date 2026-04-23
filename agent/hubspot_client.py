"""
HubSpot CRM Client
Every conversation event logged. Custom properties for ICP data.
"""

import json
from datetime import datetime
from typing import Optional

import config


class HubSpotClient:
    """
    HubSpot Developer Sandbox integration.
    Creates/updates contacts, companies, deals, and logs timeline events.
    """

    def __init__(self):
        self.access_token = config.HUBSPOT_ACCESS_TOKEN
        self._client = None
        self._init_client()

    def _init_client(self):
        """Initialize HubSpot client."""
        try:
            from hubspot import HubSpot
            if self.access_token and not self.access_token.startswith("pat-..."):
                self._client = HubSpot(access_token=self.access_token)
        except ImportError:
            print("Warning: hubspot-api-client not available")
        except Exception as e:
            print(f"Warning: HubSpot init failed: {e}")

    def ensure_custom_properties(self):
        """Bootstrap missing schema properties."""
        if not self._client:
            return
        
        required_properties = [
            {"name": "icp_segment", "label": "ICP Segment", "type": "string", "field_type": "text", "group_name": "contactinformation"},
            {"name": "icp_confidence", "label": "ICP Confidence", "type": "string", "field_type": "text", "group_name": "contactinformation"},
            {"name": "ai_maturity_score", "label": "AI Maturity Score", "type": "string", "field_type": "text", "group_name": "contactinformation"},
            {"name": "enrichment_timestamp", "label": "Enrichment Timestamp", "type": "string", "field_type": "text", "group_name": "contactinformation"}
        ]
        
        try:
            existing = self._client.crm.properties.core_api.get_all(object_type="contacts")
            existing_names = [p.name for p in existing.results]
            
            from hubspot.crm.properties import PropertyCreate
            
            for prop in required_properties:
                if prop["name"] not in existing_names:
                    self._client.crm.properties.core_api.create(
                        object_type="contacts", 
                        property_create=PropertyCreate(**prop)
                    )
        except Exception as e:
            print(f"Warning: HubSpot property bootstrap failed: {e}")

    def create_or_update_contact(
        self,
        email: str,
        first_name: str = "",
        last_name: str = "",
        company: str = "",
        title: str = "",
        icp_segment: Optional[int] = None,
        icp_confidence: Optional[float] = None,
        ai_maturity_score: Optional[int] = None,
        enrichment_timestamp: Optional[str] = None,
    ) -> dict:
        """Create or update a contact with custom ICP properties."""
        properties = {
            "email": email,
            "firstname": first_name,
            "lastname": last_name,
            "company": company,
            "jobtitle": title,
        }
        # Custom properties
        if icp_segment is not None:
            properties["icp_segment"] = str(icp_segment)
        if icp_confidence is not None:
            properties["icp_confidence"] = str(round(icp_confidence, 2))
        if ai_maturity_score is not None:
            properties["ai_maturity_score"] = str(ai_maturity_score)
        if enrichment_timestamp:
            properties["enrichment_timestamp"] = enrichment_timestamp

        if not self._client:
            return {"status": "dry_run", "properties": properties}

        try:
            # Try to create
            from hubspot.crm.contacts import SimplePublicObjectInputForCreate
            contact_input = SimplePublicObjectInputForCreate(properties=properties)
            result = self._client.crm.contacts.basic_api.create(
                simple_public_object_input_for_create=contact_input
            )
            return {"status": "created", "id": result.id, "properties": properties}
        except Exception as e:
            error_msg = str(e)
            if "PROPERTY_DOESNT_EXIST" in error_msg:
                # Strip custom properties and retry
                safe_props = {k: v for k, v in properties.items() if k in ["email", "firstname", "lastname", "company", "jobtitle"]}
                try:
                    contact_input = SimplePublicObjectInputForCreate(properties=safe_props)
                    result = self._client.crm.contacts.basic_api.create(
                        simple_public_object_input_for_create=contact_input
                    )
                    return {"status": "created", "id": result.id, "properties": safe_props, "warning": "filtered_custom_props"}
                except Exception as e_retry:
                    return {"status": "error", "error": str(e_retry)}

            if "CONFLICT" in error_msg or "409" in error_msg:
                # Contact exists, update
                try:
                    search_result = self._client.crm.contacts.search_api.do_search(
                        public_object_search_request={
                            "filterGroups": [{"filters": [
                                {"propertyName": "email", "operator": "EQ", "value": email}
                            ]}],
                            "limit": 1
                        }
                    )
                    if search_result.results:
                        contact_id = search_result.results[0].id
                        from hubspot.crm.contacts import SimplePublicObjectInput
                        self._client.crm.contacts.basic_api.update(
                            contact_id=contact_id,
                            simple_public_object_input=SimplePublicObjectInput(properties=properties)
                        )
                        return {"status": "updated", "id": contact_id, "properties": properties}
                except Exception as e2:
                    return {"status": "error", "error": str(e2)}
            return {"status": "error", "error": str(e)}

    def create_company(
        self,
        name: str,
        domain: str = "",
        industry: str = "",
        employee_count: str = "",
        total_funding: Optional[float] = None,
    ) -> dict:
        """Create a company in HubSpot."""
        properties = {
            "name": name,
            "domain": domain,
            "industry": industry,
            "numberofemployees": employee_count,
        }
        if total_funding:
            properties["annualrevenue"] = str(total_funding)

        if not self._client:
            return {"status": "dry_run", "properties": properties}

        try:
            from hubspot.crm.companies import SimplePublicObjectInputForCreate
            result = self._client.crm.companies.basic_api.create(
                simple_public_object_input_for_create=SimplePublicObjectInputForCreate(
                    properties=properties
                )
            )
            return {"status": "created", "id": result.id}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def create_deal(
        self,
        deal_name: str,
        pipeline: str = "default",
        stage: str = "appointmentscheduled",
        amount: Optional[float] = None,
        contact_id: Optional[str] = None,
    ) -> dict:
        """Create a deal when discovery call is booked."""
        properties = {
            "dealname": deal_name,
            "pipeline": pipeline,
            "dealstage": stage,
        }
        if amount:
            properties["amount"] = str(amount)

        if not self._client:
            return {"status": "dry_run", "properties": properties}

        try:
            from hubspot.crm.deals import SimplePublicObjectInputForCreate
            result = self._client.crm.deals.basic_api.create(
                simple_public_object_input_for_create=SimplePublicObjectInputForCreate(
                    properties=properties
                )
            )
            return {"status": "created", "id": result.id}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def log_activity(self, contact_id: str, activity_type: str, body: str) -> dict:
        """Log a timeline activity (email sent, reply received, call booked)."""
        if not self._client:
            return {"status": "dry_run", "type": activity_type, "body": body[:100]}

        try:
            from hubspot.crm.objects.notes import SimplePublicObjectInputForCreate
            result = self._client.crm.objects.notes.basic_api.create(
                simple_public_object_input_for_create=SimplePublicObjectInputForCreate(
                    properties={
                        "hs_note_body": f"[{activity_type}] {body}",
                        "hs_timestamp": datetime.now().isoformat(),
                    }
                )
            )
            return {"status": "created", "id": result.id}
        except Exception as e:
            return {"status": "error", "error": str(e)}
