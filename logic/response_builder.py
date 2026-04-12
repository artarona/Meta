import json

class WhatsAppResponse:
    """
    Standardizes responses for the WhatsApp bot.
    Handles text, buttons, and lists with validation.
    """
    
    @staticmethod
    def text(body, preview_url=False):
        """Returns a standard text response type"""
        return {
            "type": "text",
            "body": body
        }

    @staticmethod
    def buttons(body, buttons, header=None, footer=None):
        """
        Returns an interactive buttons response type.
        Meta limits: max 3 buttons, title max 20 characters.
        """
        # Validate button count
        if len(buttons) > 3:
            buttons = buttons[:3]
            
        # Clean and validate button titles
        processed_buttons = []
        for btn in buttons:
            processed_buttons.append({
                "id": str(btn.get("id"))[:256],
                "title": str(btn.get("title"))[:20]
            })

        return {
            "type": "interactive_buttons",
            "body": body[:1024],
            "buttons": processed_buttons,
            "header": header[:60] if header else None,
            "footer": footer[:60] if footer else None
        }

    @staticmethod
    def list_menu(body, button_text, sections, header=None, footer=None):
        """
        Returns an interactive list response type.
        Meta limits: max 10 rows total, row title max 24 chars, section title max 24 chars.
        """
        processed_sections = []
        total_rows = 0
        
        for sec in sections[:10]:
            section_rows = []
            for row in sec.get("rows", []):
                if total_rows >= 10:
                    break
                row_data = {
                    "id": str(row.get("id"))[:200],
                    "title": str(row.get("title"))[:24]
                }
                if "description" in row and row["description"]:
                    row_data["description"] = str(row["description"])[:72]
                section_rows.append(row_data)
                total_rows += 1
            
            if section_rows:
                processed_sections.append({
                    "title": str(sec.get("title", ""))[:24],
                    "rows": section_rows
                })
            
            if total_rows >= 10:
                break

        return {
            "type": "interactive_list",
            "body": body[:1024],
            "button_text": button_text[:20],
            "sections": processed_sections,
            "header": header[:60] if header else None,
            "footer": footer[:60] if footer else None
        }

    @staticmethod
    def trigger(name, params=None):
        """Returns a special trigger string for internal routing (e.g. WELCOME_FLOW_TRIGGER)"""
        if params:
            return f"{name}|{params}"
        return name
