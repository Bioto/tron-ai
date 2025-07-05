from tron_ai.agents.google.utils import get_gmail_service, get_calendar_service

class GoogleTools:
    @staticmethod
    def list_messages(
        max_results: int = 10,
        page_token: str = None,
        q: str = None,
        label_ids: list = ["INBOX"],
        include_spam_trash: bool = False,
        user_id: str = "me",
    ):
        """
        List Gmail messages with IDs and snippets. Useful for browsing inbox or specific labels.
        
        kkwargs:
            max_results (int): Number of messages to list (max 500).
            page_token (str): Page token for pagination.
            q (str): Gmail search query (e.g., 'from:someone@example.com').
            label_ids (list): Only return messages with these label IDs.
            include_spam_trash (bool): Include messages from SPAM and TRASH.
            user_id (str): Gmail user ID (default: 'me').
        Returns:
            list: List of message dicts with id and snippet.
        """
        service = get_gmail_service()
        params = {
            "userId": user_id,
            "maxResults": max_results,
            "includeSpamTrash": include_spam_trash,
        }
        if page_token:
            params["pageToken"] = page_token
        if q:
            params["q"] = q
        if label_ids:
            params["labelIds"] = label_ids
        results = service.users().messages().list(**params).execute()
        messages = results.get("messages", [])
        output = []
        for msg in messages:
            msg_detail = service.users().messages().get(userId=user_id, id=msg["id"]).execute()
            output.append({
                "id": msg["id"],
                "snippet": msg_detail.get("snippet", "")
            })
        return output

    @staticmethod
    def read_message(
        message_id: str,
        user_id: str = "me",
        format: str = "full",
        metadata_headers: list = None,
    ):
        """
        Read full email content including subject, sender, snippet, and body text.
        
        kwargs:
            message_id (str): The Gmail message ID.
            user_id (str): Gmail user ID (default: 'me').
            format (str): Message format ('full', 'minimal', 'raw', 'metadata').
            metadata_headers (list): If format is 'metadata', which headers to include.
        Returns:
            dict: Message details (subject, from, snippet, body if available).
        """
        service = get_gmail_service()
        params = {
            "userId": user_id,
            "id": message_id,
            "format": format,
        }
        if metadata_headers:
            params["metadataHeaders"] = metadata_headers
        msg = service.users().messages().get(**params).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        subject = headers.get("Subject", "")
        sender = headers.get("From", "")
        snippet = msg.get("snippet", "")
        # Try to extract plain text body
        body = ""
        if "parts" in msg.get("payload", {}):
            for part in msg["payload"]["parts"]:
                if part["mimeType"] == "text/plain":
                    import base64
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
        return {
            "id": message_id,
            "subject": subject,
            "from": sender,
            "snippet": snippet,
            "body": body
        }

    @staticmethod
    def search_messages(
        query: str,
        max_results: int = 10,
        page_token: str = None,
        label_ids: list = None,
        include_spam_trash: bool = False,
        user_id: str = "me",
    ):
        """
        Search Gmail using powerful query syntax. Find emails by sender, date, subject, attachments, and more.
        
        kwargs:
            query (str): Gmail search query. Examples:
                - 'from:someone@example.com' - messages from specific sender
                - 'to:recipient@example.com' - messages sent to specific recipient
                - 'subject:meeting' - messages with "meeting" in subject
                - 'after:2024/01/01' - messages after specific date
                - 'before:2024/12/31' - messages before specific date
                - 'has:attachment' - messages with attachments
                - 'is:unread' - unread messages
                - 'is:starred' - starred messages
                - 'larger:10M' - messages larger than 10MB
                - 'smaller:1M' - messages smaller than 1MB
                - 'label:work' - messages with specific label
                - 'filename:pdf' - messages with PDF attachments
                - 'newer_than:1d' - messages from last day
                - 'older_than:1w' - messages older than 1 week
                - 'from:john@example.com after:2024/01/01 before:2024/12/31' - combined filters
            max_results (int): Max number of results (default: 10).
            page_token (str): Page token for pagination.
            label_ids (list): Only return messages with these label IDs.
            include_spam_trash (bool): Include messages from SPAM and TRASH.
            user_id (str): Gmail user ID (default: 'me').
        Returns:
            list: List of message dicts with id and snippet.
        """
        response = GoogleTools.list_messages(
            max_results=max_results,
            page_token=page_token,
            q=query,
            label_ids=label_ids,
            include_spam_trash=include_spam_trash,
            user_id=user_id,
        )
        
        print("Search Messages Response:")
        print(response)
        
        return response

    @staticmethod
    def list_events(max_results: int = 10):
        """
        List upcoming Google Calendar events in chronological order.
        
        kwargs:
            max_results (int): Number of events to list.
        Returns:
            list: List of event dicts with id, summary, start, end, and description.
        """
        service = get_calendar_service()
        events_result = service.events().list(
            calendarId='primary',
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime',
            timeMin=None  # Could set to now, but None lists all
        ).execute()
        events = events_result.get('items', [])
        output = []
        for event in events:
            output.append({
                'id': event.get('id'),
                'summary': event.get('summary', ''),
                'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')),
                'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date', '')),
                'description': event.get('description', '')
            })
            
        print(output)
        return output

    @staticmethod
    def search_events(query: str, max_results: int = 10, time_min: str = None, time_max: str = None, 
                     calendar_id: str = 'primary', single_events: bool = True, order_by: str = 'startTime',
                     show_deleted: bool = False, updated_min: str = None, private_extended_property: str = None,
                     shared_extended_property: str = None, time_zone: str = None):
        """
        Search calendar events by text (searches in summary, description, location, attendee names).
        
        kwargs:
            query (str): Search string. Using the Google Calendar API's q parameter.
            max_results (int): Max number of results.
            time_min (str): Start time for search range (ISO 8601 format).
            time_max (str): End time for search range (ISO 8601 format).
            calendar_id (str): Calendar ID to search in (default: 'primary').
            single_events (bool): Whether to expand recurring events into instances.
            order_by (str): Order of events ('startTime' or 'updated').
            show_deleted (bool): Whether to include deleted events.
            updated_min (str): Lower bound for event last modification time.
            private_extended_property (str): Private extended property filter.
            shared_extended_property (str): Shared extended property filter.
            time_zone (str): Time zone used in the response.
        Returns:
            list: List of event dicts with id, summary, start, end, and description.
        """
        service = get_calendar_service()
        events_result = service.events().list(
            calendarId=calendar_id,
            q=query,
            maxResults=max_results,
            singleEvents=single_events,
            orderBy=order_by,
            timeMin=time_min,
            timeMax=time_max,
            showDeleted=show_deleted,
            updatedMin=updated_min,
            privateExtendedProperty=private_extended_property,
            sharedExtendedProperty=shared_extended_property,
            timeZone=time_zone
        ).execute()
        events = events_result.get('items', [])
        output = []
        for event in events:
            output.append({
                'id': event.get('id'),
                'summary': event.get('summary', ''),
                'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')),
                'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date', '')),
                'description': event.get('description', '')
            })
        return output

    @staticmethod
    def read_event(event_id: str, calendar_id: str = 'primary', time_zone: str = None, 
                   always_include_email: bool = True, max_attendees: int = None, 
                   single_events: bool = True, original_start: str = None):
        """
        Get detailed information about a specific calendar event including attendees, location, and conference links.
        
        kwargs:
            event_id (str): The event ID.
            calendar_id (str): Calendar ID (default: 'primary').
            time_zone (str): Time zone used in the response.
            always_include_email (bool): Whether to always include email in attendee info.
            max_attendees (int): Maximum number of attendees to include.
            single_events (bool): Whether to expand recurring events into instances.
            original_start (str): Original start time for recurring events.
        Returns:
            dict: Event details (id, summary, start, end, description, location, attendees, 
                  creator, organizer, status, visibility, transparency, recurring_event_id, 
                  html_link, created, updated, guests_can_modify, guests_can_invite_others, 
                  guests_can_see_other_guests, reminders, conference_data, hangout_link, 
                  meet_link, source, attachments, event_type, color_id, locked).
        """
        service = get_calendar_service()
        event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id,
            timeZone=time_zone,
            alwaysIncludeEmail=always_include_email,
            maxAttendees=max_attendees,
            singleEvents=single_events,
            originalStart=original_start
        ).execute()
        
        return {
            'id': event.get('id'),
            'summary': event.get('summary', ''),
            'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')),
            'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date', '')),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'attendees': [a.get('email') for a in event.get('attendees', [])] if 'attendees' in event else [],
            'creator': event.get('creator', {}),
            'organizer': event.get('organizer', {}),
            'status': event.get('status', ''),
            'visibility': event.get('visibility', ''),
            'transparency': event.get('transparency', ''),
            'recurring_event_id': event.get('recurringEventId', ''),
            'html_link': event.get('htmlLink', ''),
            'created': event.get('created', ''),
            'updated': event.get('updated', ''),
            'guests_can_modify': event.get('guestsCanModify', False),
            'guests_can_invite_others': event.get('guestsCanInviteOthers', True),
            'guests_can_see_other_guests': event.get('guestsCanSeeOtherGuests', True),
            'reminders': event.get('reminders', {}),
            'conference_data': event.get('conferenceData', {}),
            'hangout_link': event.get('hangoutLink', ''),
            'meet_link': event.get('meetLink', ''),
            'source': event.get('source', {}),
            'attachments': event.get('attachments', []),
            'event_type': event.get('eventType', ''),
            'color_id': event.get('colorId', ''),
            'locked': event.get('locked', False)
        }

    @staticmethod
    def send_message(
        to: str,
        subject: str,
        body: str,
        cc: str = None,
        bcc: str = None,
        attachments: list = None,
        user_id: str = "me",
        is_html: bool = False,
    ):
        """
        Compose and send an email with optional attachments, CC, and BCC recipients.
        
        kwargs:
            to (str): Recipient email address.
            subject (str): Email subject.
            body (str): Email body (plain text or HTML).
            cc (str): CC recipient(s), comma-separated.
            bcc (str): BCC recipient(s), comma-separated.
            attachments (list): List of file paths to attach.
            user_id (str): Gmail user ID (default: 'me').
            is_html (bool): If True, body is HTML.
        Returns:
            dict: Sent message metadata.
        """
        import base64
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders
        import os

        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = subject
        if cc:
            message["cc"] = cc
        if bcc:
            message["bcc"] = bcc
        mime_body = MIMEText(body, "html" if is_html else "plain")
        message.attach(mime_body)
        if attachments:
            for file_path in attachments:
                filename = os.path.basename(file_path)
                with open(file_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={filename}",
                )
                message.attach(part)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service = get_gmail_service()
        sent = service.users().messages().send(
            userId=user_id, body={"raw": raw}
        ).execute()
        return sent

    @staticmethod
    def modify_message_labels(
        message_id: str,
        add_label_ids: list = None,
        remove_label_ids: list = None,
        user_id: str = "me",
    ):
        """
        Apply or remove labels to organize emails (e.g., move to folders, mark as important).
        
        kwargs:
            message_id (str): The Gmail message ID.
            add_label_ids (list): List of label IDs to add.
            remove_label_ids (list): List of label IDs to remove.
            user_id (str): Gmail user ID (default: 'me').
        Returns:
            dict: Modified message metadata.
        """
        service = get_gmail_service()
        body = {}
        if add_label_ids:
            body["addLabelIds"] = add_label_ids
        if remove_label_ids:
            body["removeLabelIds"] = remove_label_ids
        return service.users().messages().modify(userId=user_id, id=message_id, body=body).execute()

    @staticmethod
    def delete_message(message_id: str, user_id: str = "me"):
        """
        Delete the message. Message can be recovered within 30 days.
        
        kwargs:
            message_id (str): The Gmail message ID.
            user_id (str): Gmail user ID (default: 'me').
        Returns:
            dict: Trashed message metadata.
        """
        try:
            service = get_gmail_service()
            response = service.users().messages().trash(userId=user_id, id=message_id).execute()
        except Exception as e:
            print(e)
            response = None
        print("Delete Message Response:")
        print(response)
        return response

    @staticmethod
    def undelete_message(message_id: str, user_id: str = "me"):
        """
        Restore email from trash back to inbox.
        
        kwargs:
            message_id (str): The Gmail message ID.
            user_id (str): Gmail user ID (default: 'me').
        Returns:
            dict: Untrashed message metadata.
        """
        service = get_gmail_service()
        return service.users().messages().untrash(userId=user_id, id=message_id).execute()
