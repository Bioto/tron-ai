from tron_ai.agents.google.utils import get_gmail_service, get_calendar_service
import re
import logging

logger = logging.getLogger(__name__)

class GoogleTools:
    @staticmethod
    def _clean_snippet(snippet: str) -> str:
        """Clean up email snippet by removing excessive whitespace and special characters."""
        # Remove zero-width characters and excessive whitespace
        cleaned = re.sub(r'[\u200c\u200d\u2060\ufeff\u180e\u2000-\u200b]+', ' ', snippet)
        # Replace multiple spaces with single space
        cleaned = re.sub(r'\s+', ' ', cleaned)
        # Strip leading/trailing whitespace
        cleaned = cleaned.strip()
        return cleaned
    
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
        List Gmail messages with IDs and snippets ordered from most recent to oldest. 
        Useful for browsing inbox or specific labels.
        
        kkwargs:
            max_results (int): Number of messages to list (max 500).
            page_token (str): Page token for pagination.
            q (str): Gmail search query (e.g., 'from:someone@example.com').
            label_ids (list): Only return messages with these label IDs.
            include_spam_trash (bool): Include messages from SPAM and TRASH.
            user_id (str): Gmail user ID (default: 'me').
        Returns:
            list: List of message dicts with id and snippet, ordered from most recent to oldest.
        """
        logger.info(f"list_messages called with max_results={max_results}, q='{q}', label_ids={label_ids}")
        
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
        
        logger.info(f"Gmail API returned {len(messages)} messages")
        
        output = []
        for i, msg in enumerate(messages):
            logger.debug(f"Processing message {i+1}/{len(messages)}: ID={msg['id']}")
            msg_detail = service.users().messages().get(userId=user_id, id=msg["id"]).execute()
            raw_snippet = msg_detail.get("snippet", "")
            cleaned_snippet = GoogleTools._clean_snippet(raw_snippet)
            output.append({
                "id": msg["id"],
                "snippet": cleaned_snippet
            })
            logger.debug(f"  Added message: ID={msg['id']}, snippet_length={len(cleaned_snippet)}")
        
        logger.info(f"list_messages returning {len(output)} processed messages")
        
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
        Results are ordered from most recent to oldest.
        
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
            list: List of message dicts with id and snippet, ordered from most recent to oldest.
        """
        logger.info(f"search_messages called with query='{query}', max_results={max_results}")
        
        response = GoogleTools.list_messages(
            max_results=max_results,
            page_token=page_token,
            q=query,
            label_ids=label_ids,
            include_spam_trash=include_spam_trash,
            user_id=user_id,
        )
        
        logger.info(f"search_messages returning {len(response)} results")
        for i, msg in enumerate(response):
            logger.debug(f"  Result {i+1}: ID={msg.get('id', 'unknown')}, snippet_length={len(msg.get('snippet', ''))}")
        
        return response

    @staticmethod
    def list_events(max_results: int = 10):
        """
        List Google Calendar events ordered from most recent to oldest.
        
        kwargs:
            max_results (int): Number of events to list.
        Returns:
            list: List of event dicts with id, summary, start, end, and description.
        """
        import datetime
        service = get_calendar_service()
        
        # Get current time in ISO format
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        
        # First, get upcoming events
        upcoming_events_result = service.events().list(
            calendarId='primary',
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime',
            timeMin=now
        ).execute()
        upcoming_events = upcoming_events_result.get('items', [])
        
        # Then, get past events (most recent first)
        past_events_result = service.events().list(
            calendarId='primary',
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime',
            timeMax=now
        ).execute()
        past_events = past_events_result.get('items', [])
        
        # Reverse past events to get most recent first
        past_events.reverse()
        
        # Combine: upcoming events first (soonest first), then past events (most recent first)
        all_events = upcoming_events + past_events
        
        # Limit to max_results
        all_events = all_events[:max_results]
        
        output = []
        for event in all_events:
            output.append({
                'id': event.get('id'),
                'summary': event.get('summary', ''),
                'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')),
                'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date', '')),
                'description': event.get('description', '')
            })
            
        return output

    @staticmethod
    def search_events(query: str, max_results: int = 10, time_min: str = None, time_max: str = None, 
                     calendar_id: str = 'primary', single_events: bool = True, order_by: str = 'startTime',
                     show_deleted: bool = False, updated_min: str = None, private_extended_property: str = None,
                     shared_extended_property: str = None, time_zone: str = None):
        """
        Search calendar events by text (searches in summary, description, location, attendee names).
        Results are ordered based on order_by parameter (default: by start time).
        
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
        import datetime
        service = get_calendar_service()
        
        # If no time range specified, search both past and future events
        if time_min is None and time_max is None:
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            
            # Search upcoming events
            upcoming_params = {
                'calendarId': calendar_id,
                'q': query,
                'maxResults': max_results,
                'singleEvents': single_events,
                'orderBy': order_by,
                'timeMin': now,
                'showDeleted': show_deleted,
                'updatedMin': updated_min,
                'privateExtendedProperty': private_extended_property,
                'sharedExtendedProperty': shared_extended_property,
                'timeZone': time_zone
            }
            upcoming_result = service.events().list(**{k: v for k, v in upcoming_params.items() if v is not None}).execute()
            upcoming_events = upcoming_result.get('items', [])
            
            # Search past events
            past_params = {
                'calendarId': calendar_id,
                'q': query,
                'maxResults': max_results,
                'singleEvents': single_events,
                'orderBy': order_by,
                'timeMax': now,
                'showDeleted': show_deleted,
                'updatedMin': updated_min,
                'privateExtendedProperty': private_extended_property,
                'sharedExtendedProperty': shared_extended_property,
                'timeZone': time_zone
            }
            past_result = service.events().list(**{k: v for k, v in past_params.items() if v is not None}).execute()
            past_events = past_result.get('items', [])
            
            # Reverse past events to get most recent first
            past_events.reverse()
            
            # Combine: upcoming events first, then past events
            events = upcoming_events + past_events
            
            # Limit to max_results
            events = events[:max_results]
        else:
            # Use provided time range
            params = {
                'calendarId': calendar_id,
                'q': query,
                'maxResults': max_results,
                'singleEvents': single_events,
                'orderBy': order_by,
                'timeMin': time_min,
                'timeMax': time_max,
                'showDeleted': show_deleted,
                'updatedMin': updated_min,
                'privateExtendedProperty': private_extended_property,
                'sharedExtendedProperty': shared_extended_property,
                'timeZone': time_zone
            }
            events_result = service.events().list(**{k: v for k, v in params.items() if v is not None}).execute()
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
    def create_event(
        summary: str,
        start_time: str,
        end_time: str,
        description: str = None,
        location: str = None,
        attendees: list = None,
        calendar_id: str = 'primary',
        time_zone: str = None,
        recurrence: list = None,
        reminders: dict = None,
        visibility: str = 'default',
        transparency: str = 'opaque',
        color_id: str = None,
        conference_data_version: int = None,
        send_notifications: bool = True,
        send_updates: str = 'all',
        supports_attachments: bool = False,
        guests_can_invite_others: bool = True,
        guests_can_modify: bool = False,
        guests_can_see_other_guests: bool = True,
    ):
        """
        Create a new calendar event with specified details.
        
        kwargs:
            summary (str): Event title/summary (required).
            start_time (str): Event start time in ISO 8601 format (e.g., '2024-12-25T10:00:00-07:00') (required).
            end_time (str): Event end time in ISO 8601 format (required).
            description (str): Event description/notes.
            location (str): Event location (physical address or meeting link).
            attendees (list): List of attendee email addresses.
            calendar_id (str): Calendar ID to create event in (default: 'primary').
            time_zone (str): Time zone for the event (e.g., 'America/New_York').
            recurrence (list): Recurrence rules in RRULE format (e.g., ['RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR']).
            reminders (dict): Custom reminders (e.g., {'useDefault': False, 'overrides': [{'method': 'email', 'minutes': 30}]}).
            visibility (str): Event visibility ('default', 'public', 'private', 'confidential').
            transparency (str): Show time as busy or free ('opaque' for busy, 'transparent' for free).
            color_id (str): Event color ID (1-11).
            conference_data_version (int): Version number of conference data (use 1 to enable).
            send_notifications (bool): Whether to send notifications about event creation.
            send_updates (str): Who to send updates to ('all', 'externalOnly', 'none').
            supports_attachments (bool): Whether the event supports attachments.
            guests_can_invite_others (bool): Whether guests can invite others.
            guests_can_modify (bool): Whether guests can modify the event.
            guests_can_see_other_guests (bool): Whether guests can see other guests.
        Returns:
            dict: Created event details.
        """
        service = get_calendar_service()
        
        # Build event body
        event_body = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': time_zone} if time_zone else {'dateTime': start_time},
            'end': {'dateTime': end_time, 'timeZone': time_zone} if time_zone else {'dateTime': end_time},
            'visibility': visibility,
            'transparency': transparency,
            'guestsCanInviteOthers': guests_can_invite_others,
            'guestsCanModify': guests_can_modify,
            'guestsCanSeeOtherGuests': guests_can_see_other_guests,
        }
        
        if description:
            event_body['description'] = description
        if location:
            event_body['location'] = location
        if attendees:
            event_body['attendees'] = [{'email': email} for email in attendees]
        if recurrence:
            event_body['recurrence'] = recurrence
        if reminders:
            event_body['reminders'] = reminders
        if color_id:
            event_body['colorId'] = color_id
        
        # Create the event
        params = {
            'calendarId': calendar_id,
            'body': event_body,
            'sendNotifications': send_notifications,
            'sendUpdates': send_updates,
            'supportsAttachments': supports_attachments,
        }
        
        if conference_data_version:
            params['conferenceDataVersion'] = conference_data_version
            
        event = service.events().insert(**params).execute()
        
        logger.info(f"Created event with ID: {event.get('id')}")
        
        return {
            'id': event.get('id'),
            'summary': event.get('summary', ''),
            'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')),
            'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date', '')),
            'html_link': event.get('htmlLink', ''),
            'created': event.get('created', ''),
            'status': event.get('status', ''),
        }

    @staticmethod
    def update_event(
        event_id: str,
        calendar_id: str = 'primary',
        summary: str = None,
        start_time: str = None,
        end_time: str = None,
        description: str = None,
        location: str = None,
        attendees: list = None,
        time_zone: str = None,
        recurrence: list = None,
        reminders: dict = None,
        visibility: str = None,
        transparency: str = None,
        color_id: str = None,
        conference_data_version: int = None,
        send_notifications: bool = True,
        send_updates: str = 'all',
        supports_attachments: bool = False,
        guests_can_invite_others: bool = None,
        guests_can_modify: bool = None,
        guests_can_see_other_guests: bool = None,
        status: str = None,
    ):
        """
        Update an existing calendar event. Only provided fields will be updated.
        
        kwargs:
            event_id (str): The event ID to update (required).
            calendar_id (str): Calendar ID (default: 'primary').
            summary (str): New event title/summary.
            start_time (str): New start time in ISO 8601 format.
            end_time (str): New end time in ISO 8601 format.
            description (str): New event description.
            location (str): New event location.
            attendees (list): New list of attendee email addresses (replaces existing).
            time_zone (str): Time zone for the event.
            recurrence (list): New recurrence rules (replaces existing).
            reminders (dict): New reminders configuration.
            visibility (str): Event visibility ('default', 'public', 'private', 'confidential').
            transparency (str): Show time as busy or free ('opaque', 'transparent').
            color_id (str): Event color ID (1-11).
            conference_data_version (int): Version number of conference data.
            send_notifications (bool): Whether to send notifications about the update.
            send_updates (str): Who to send updates to ('all', 'externalOnly', 'none').
            supports_attachments (bool): Whether the event supports attachments.
            guests_can_invite_others (bool): Whether guests can invite others.
            guests_can_modify (bool): Whether guests can modify the event.
            guests_can_see_other_guests (bool): Whether guests can see other guests.
            status (str): Event status ('confirmed', 'tentative', 'cancelled').
        Returns:
            dict: Updated event details.
        """
        service = get_calendar_service()
        
        # First, get the current event to preserve existing data
        current_event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        # Update only the provided fields
        if summary is not None:
            current_event['summary'] = summary
        if description is not None:
            current_event['description'] = description
        if location is not None:
            current_event['location'] = location
        if start_time is not None:
            current_event['start'] = {'dateTime': start_time, 'timeZone': time_zone} if time_zone else {'dateTime': start_time}
        if end_time is not None:
            current_event['end'] = {'dateTime': end_time, 'timeZone': time_zone} if time_zone else {'dateTime': end_time}
        if attendees is not None:
            current_event['attendees'] = [{'email': email} for email in attendees]
        if recurrence is not None:
            current_event['recurrence'] = recurrence
        if reminders is not None:
            current_event['reminders'] = reminders
        if visibility is not None:
            current_event['visibility'] = visibility
        if transparency is not None:
            current_event['transparency'] = transparency
        if color_id is not None:
            current_event['colorId'] = color_id
        if guests_can_invite_others is not None:
            current_event['guestsCanInviteOthers'] = guests_can_invite_others
        if guests_can_modify is not None:
            current_event['guestsCanModify'] = guests_can_modify
        if guests_can_see_other_guests is not None:
            current_event['guestsCanSeeOtherGuests'] = guests_can_see_other_guests
        if status is not None:
            current_event['status'] = status
        
        # Update the event
        params = {
            'calendarId': calendar_id,
            'eventId': event_id,
            'body': current_event,
            'sendNotifications': send_notifications,
            'sendUpdates': send_updates,
            'supportsAttachments': supports_attachments,
        }
        
        if conference_data_version:
            params['conferenceDataVersion'] = conference_data_version
            
        updated_event = service.events().update(**params).execute()
        
        logger.info(f"Updated event with ID: {updated_event.get('id')}")
        
        return {
            'id': updated_event.get('id'),
            'summary': updated_event.get('summary', ''),
            'start': updated_event.get('start', {}).get('dateTime', updated_event.get('start', {}).get('date', '')),
            'end': updated_event.get('end', {}).get('dateTime', updated_event.get('end', {}).get('date', '')),
            'html_link': updated_event.get('htmlLink', ''),
            'updated': updated_event.get('updated', ''),
            'status': updated_event.get('status', ''),
        }

    @staticmethod
    def delete_event(
        event_id: str,
        calendar_id: str = 'primary',
        send_notifications: bool = True,
        send_updates: str = 'all',
    ):
        """
        Delete a calendar event.
        
        kwargs:
            event_id (str): The event ID to delete (required).
            calendar_id (str): Calendar ID (default: 'primary').
            send_notifications (bool): Whether to send notifications about the deletion.
            send_updates (str): Who to send updates to ('all', 'externalOnly', 'none').
        Returns:
            dict: Confirmation of deletion with event_id.
        """
        service = get_calendar_service()
        
        try:
            service.events().delete(
                calendarId=calendar_id,
                eventId=event_id,
                sendNotifications=send_notifications,
                sendUpdates=send_updates
            ).execute()
            
            logger.info(f"Deleted event with ID: {event_id}")
            
            return {
                'success': True,
                'event_id': event_id,
                'message': f'Event {event_id} successfully deleted'
            }
        except Exception as e:
            logger.error(f"Failed to delete event {event_id}: {str(e)}")
            return {
                'success': False,
                'event_id': event_id,
                'error': str(e)
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
    def reply_to_message(
        message_id: str,
        body: str,
        to: str = None,
        cc: str = None,
        bcc: str = None,
        attachments: list = None,
        user_id: str = "me",
        is_html: bool = False,
        include_original: bool = True,
        reply_all: bool = False,
    ):
        """
        Reply to an existing email message, maintaining the email thread.
        
        kwargs:
            message_id (str): The Gmail message ID to reply to (required).
            body (str): Reply body (plain text or HTML) (required).
            to (str): Override recipient email address (optional - defaults to original sender).
            cc (str): CC recipient(s), comma-separated.
            bcc (str): BCC recipient(s), comma-separated.
            attachments (list): List of file paths to attach.
            user_id (str): Gmail user ID (default: 'me').
            is_html (bool): If True, body is HTML.
            include_original (bool): If True, includes the original message in the reply.
            reply_all (bool): If True, replies to all recipients of the original message.
        Returns:
            dict: Sent reply message metadata.
        """
        import base64
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders
        import os
        
        service = get_gmail_service()
        
        # Get the original message to extract threading information
        original_msg = service.users().messages().get(
            userId=user_id, 
            id=message_id,
            format='full'
        ).execute()
        
        # Extract headers from original message
        headers = {}
        for header in original_msg.get('payload', {}).get('headers', []):
            headers[header['name']] = header['value']
        
        # Get original subject and prepend "Re:" if not already present
        original_subject = headers.get('Subject', '')
        if not original_subject.startswith('Re:'):
            subject = f"Re: {original_subject}"
        else:
            subject = original_subject
        
        # Determine recipients
        if to is None:
            # Default to replying to the sender
            to = headers.get('From', '')
        
        if reply_all and not to:
            # Extract all recipients from original message
            original_to = headers.get('To', '')
            original_cc = headers.get('Cc', '')
            # Parse and combine recipients (simplified - in production you'd want proper email parsing)
            all_recipients = []
            if original_to:
                all_recipients.extend(original_to.split(','))
            if original_cc:
                all_recipients.extend(original_cc.split(','))
            # Remove duplicates and self
            all_recipients = list(set(r.strip() for r in all_recipients))
            # Set recipients
            if all_recipients:
                to = all_recipients[0] if len(all_recipients) > 0 else ''
                if len(all_recipients) > 1:
                    cc = ', '.join(all_recipients[1:]) if not cc else f"{cc}, {', '.join(all_recipients[1:])}"
        
        # Create the reply message
        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = subject
        if cc:
            message["cc"] = cc
        if bcc:
            message["bcc"] = bcc
        
        # Add threading headers
        message_id_header = headers.get('Message-ID', '')
        if message_id_header:
            message["In-Reply-To"] = message_id_header
            message["References"] = headers.get('References', '') + ' ' + message_id_header
        
        # Add thread ID to maintain conversation threading
        thread_id = original_msg.get('threadId')
        
        # Construct the reply body
        reply_body = body
        
        if include_original:
            # Get the original message body
            original_body = ""
            original_snippet = original_msg.get('snippet', '')
            
            # Try to extract the full body
            payload = original_msg.get('payload', {})
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part.get('body', {}).get('data', '')
                        if data:
                            original_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                            break
            elif payload.get('body', {}).get('data'):
                # Single part message
                data = payload['body']['data']
                original_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            
            # Use snippet if body extraction failed
            if not original_body:
                original_body = original_snippet
            
            # Format the reply with original message quoted
            original_from = headers.get('From', 'Unknown')
            original_date = headers.get('Date', 'Unknown date')
            
            if is_html:
                reply_body = f"""
{body}

<br><br>
<div style="border-left: 2px solid #ccc; padding-left: 10px; margin-left: 10px;">
On {original_date}, {original_from} wrote:<br><br>
{original_body.replace(chr(10), '<br>')}
</div>
"""
            else:
                reply_body = f"""
{body}

On {original_date}, {original_from} wrote:

{chr(10).join('> ' + line for line in original_body.split(chr(10)))}
"""
        
        # Attach the body
        mime_body = MIMEText(reply_body, "html" if is_html else "plain")
        message.attach(mime_body)
        
        # Add attachments if provided
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
        
        # Encode and send the message
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send with thread ID to maintain conversation
        send_body = {"raw": raw}
        if thread_id:
            send_body["threadId"] = thread_id
            
        sent = service.users().messages().send(
            userId=user_id, 
            body=send_body
        ).execute()
        
        logger.info(f"Sent reply to message {message_id}")
        
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
