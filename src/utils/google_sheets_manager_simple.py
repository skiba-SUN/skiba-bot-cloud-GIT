"""Google Sheets lead management system - Simplified OAuth version"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
import pytz
import os
import pickle

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Scopes required for Google Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]


class GoogleSheetsManager:
    """Manages lead data in Google Sheets"""

    # Status options (same as LeadManager)
    STATUS_NEW = "חדש"
    STATUS_IN_CONVERSATION = "בשיחה"
    STATUS_CALL_SCHEDULED = "נקבעה שיחה"
    STATUS_CLOSED = "נסגר"
    STATUS_NOT_SUITABLE = "לא מתאים"

    # Experience levels
    EXPERIENCE_BEGINNER = "מתחיל"
    EXPERIENCE_INTERMEDIATE = "בינוני"
    EXPERIENCE_ADVANCED = "מתקדם"

    # Goals
    GOAL_FITNESS = "כושר"
    GOAL_BOXING = "אגרוף"
    GOAL_HEALING = "ריפוי"
    GOAL_EXTREME = "אקסטרים"

    # Destinations
    DEST_PHUKET = "פוקט"
    DEST_CHIANG_MAI = "צ'אנג מאי"
    DEST_OTHER = "אחר"

    def __init__(self, spreadsheet_id: str):
        """
        Initialize Google Sheets manager

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
        """
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = "Leads"  # Name of the sheet tab

        # Column headers (A-S = 19 columns)
        self.columns = [
            "timestamp",              # A
            "source",                 # B
            "name",                   # C
            "phone",                  # D
            "status",                 # E
            "match_score",            # F
            "destination",            # G
            "experience",             # H
            "goals",                  # I
            "conversation_summary",   # J
            "reminder_date",          # K
            "notes",                  # L
            "whatsapp_id",            # M
            "last_message_time",      # N
            "message_count",          # O
            "rejects",               # P - objections (admitted + suspected)
            "meeting",               # Q - scheduled meeting details
            "age",                   # R
            "location",              # S - where in Israel
        ]
        self._last_col = "S"

        # Set up Google Sheets API
        try:
            credentials = self._get_credentials()
            self.service = build('sheets', 'v4', credentials=credentials)
            self.sheets = self.service.spreadsheets()

            # Initialize sheet if needed
            self._initialize_sheet()

            logger.info(f"Connected to Google Sheets: {spreadsheet_id}")

        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {str(e)}")
            raise

    def _get_credentials(self):
        """Get or refresh OAuth credentials"""
        creds = None
        token_file = 'token.pickle'
        credentials_file = 'credentials.json'

        # Check if credentials file exists
        if not os.path.exists(credentials_file):
            raise FileNotFoundError(
                f"Credentials file not found: {credentials_file}\n"
                "Please download it from Google Cloud Console and save as credentials.json"
            )

        # Load existing token
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # This will open browser for authentication
                print("\n" + "="*70)
                print("GOOGLE AUTHENTICATION REQUIRED")
                print("="*70)
                logger.info("Opening browser for Google authentication...")
                logger.info("Please select your account and allow access to Google Sheets")

                # Use the credentials.json file
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file,
                    scopes=SCOPES
                )

                print("\nIf browser doesn't open automatically, copy this URL:")
                print("-" * 70)

                creds = flow.run_local_server(
                    port=0,
                    open_browser=True,
                    authorization_prompt_message='\nPlease visit this URL: {url}'
                )

            # Save credentials for next time
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)

        return creds

    def _initialize_sheet(self):
        """Initialize sheet with headers if empty"""
        try:
            # Try to read first row
            result = self.sheets.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A1:S1'
            ).execute()

            values = result.get('values', [])

            # If empty, write headers
            if not values:
                self.sheets.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{self.sheet_name}!A1:S1',
                    valueInputOption='RAW',
                    body={'values': [self.columns]}
                ).execute()

                logger.info("Initialized Google Sheet with headers")

        except HttpError as e:
            if e.resp.status == 404:
                logger.error("Spreadsheet not found. Check the ID and sharing permissions.")
                raise
            elif e.resp.status == 400 and "Unable to parse range" in str(e):
                # Sheet doesn't exist, create it
                logger.info(f"Sheet '{self.sheet_name}' not found. Creating it...")
                try:
                    request_body = {
                        'requests': [{
                            'addSheet': {
                                'properties': {
                                    'title': self.sheet_name
                                }
                            }
                        }]
                    }
                    self.service.spreadsheets().batchUpdate(
                        spreadsheetId=self.spreadsheet_id,
                        body=request_body
                    ).execute()

                    logger.info(f"Created sheet '{self.sheet_name}'")

                    # Now add headers
                    self.sheets.values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=f'{self.sheet_name}!A1:S1',
                        valueInputOption='RAW',
                        body={'values': [self.columns]}
                    ).execute()

                    logger.info("Added headers to new sheet")

                except Exception as create_error:
                    logger.error(f"Failed to create sheet: {str(create_error)}")
                    raise
            else:
                logger.error(f"Error initializing sheet: {str(e)}")
                raise

    def _get_all_rows(self) -> List[List]:
        """Get all rows from sheet"""
        try:
            result = self.sheets.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A2:S'  # Skip header row
            ).execute()

            return result.get('values', [])

        except HttpError as e:
            logger.error(f"Error reading sheet: {str(e)}")
            return []

    def _row_to_dict(self, row: List) -> Dict:
        """Convert row list to dictionary"""
        # Pad row with empty strings if needed
        while len(row) < len(self.columns):
            row.append('')

        return {col: val for col, val in zip(self.columns, row)}

    def _dict_to_row(self, data: Dict) -> List:
        """Convert dictionary to row list"""
        return [str(data.get(col, '')) for col in self.columns]

    def add_lead(self, lead_data: Dict) -> bool:
        """Add a new lead to Google Sheets"""
        try:
            if 'timestamp' not in lead_data:
                tz = pytz.timezone('Asia/Bangkok')
                lead_data['timestamp'] = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

            if 'status' not in lead_data:
                lead_data['status'] = self.STATUS_NEW

            if 'match_score' not in lead_data:
                lead_data['match_score'] = 0

            new_row = self._dict_to_row(lead_data)

            self.sheets.values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A:S',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [new_row]}
            ).execute()

            logger.info(f"Added new lead: {lead_data.get('name', 'Unknown')}")
            return True

        except Exception as e:
            logger.error(f"Error adding lead: {str(e)}")
            return False

    def update_lead(self, phone: str, updates: Dict) -> bool:
        """Update existing lead by phone number"""
        try:
            rows = self._get_all_rows()
            phone_col_idx = self.columns.index('phone')
            row_num = None

            for idx, row in enumerate(rows):
                if len(row) > phone_col_idx and row[phone_col_idx] == phone:
                    row_num = idx + 2
                    break

            if row_num is None:
                logger.warning(f"Lead not found with phone: {phone}")
                return False

            current_data = self._row_to_dict(rows[row_num - 2])

            for key, value in updates.items():
                if key in self.columns:
                    current_data[key] = value

            updated_row = self._dict_to_row(current_data)

            self.sheets.values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A{row_num}:S{row_num}',
                valueInputOption='RAW',
                body={'values': [updated_row]}
            ).execute()

            logger.info(f"Updated lead: {phone}")
            return True

        except Exception as e:
            logger.error(f"Error updating lead: {str(e)}")
            return False

    def get_lead(self, phone: str) -> Optional[Dict]:
        """Get lead by phone number"""
        try:
            rows = self._get_all_rows()
            phone_col_idx = self.columns.index('phone')

            for row in rows:
                if len(row) > phone_col_idx and row[phone_col_idx] == phone:
                    return self._row_to_dict(row)

            return None

        except Exception as e:
            logger.error(f"Error getting lead: {str(e)}")
            return None

    def get_lead_row_number(self, phone: str) -> Optional[int]:
        """Get the sheet row number for a lead by phone number"""
        try:
            rows = self._get_all_rows()
            phone_col_idx = self.columns.index('phone')
            for idx, row in enumerate(rows):
                if len(row) > phone_col_idx and row[phone_col_idx] == phone:
                    return idx + 2  # +2 for header row + 0-indexing
            return None
        except Exception as e:
            logger.error(f"Error getting lead row number: {str(e)}")
            return None

    def get_all_leads(self, status: Optional[str] = None) -> List[Dict]:
        """Get all leads, optionally filtered by status"""
        try:
            rows = self._get_all_rows()
            leads = [self._row_to_dict(row) for row in rows]

            if status:
                status_col = 'status'
                leads = [lead for lead in leads if lead.get(status_col) == status]

            return leads

        except Exception as e:
            logger.error(f"Error getting leads: {str(e)}")
            return []

    def calculate_match_score(self, lead_data: Dict) -> int:
        """Calculate lead matching score (0-100)"""
        score = 0

        if lead_data.get('goals'):
            score += 20

        experience = lead_data.get('experience', '')
        if experience in [self.EXPERIENCE_BEGINNER, self.EXPERIENCE_INTERMEDIATE]:
            score += 15

        if lead_data.get('destination') in [self.DEST_PHUKET, self.DEST_CHIANG_MAI]:
            score += 15

        summary = lead_data.get('conversation_summary', '')
        if len(summary) > 50:
            score += 20

        if lead_data.get('reminder_date'):
            score += 15

        try:
            message_count = int(lead_data.get('message_count', 0))
            if message_count >= 5:
                score += 15
            elif message_count >= 3:
                score += 10
            elif message_count >= 1:
                score += 5
        except (ValueError, TypeError):
            pass

        return min(score, 100)

    def get_leads_needing_followup(self) -> List[Dict]:
        """Get leads that need follow-up"""
        try:
            leads = self.get_all_leads()
            today = datetime.now().date()

            followup_leads = []
            for lead in leads:
                reminder_date_str = lead.get('reminder_date', '')
                status = lead.get('status', '')

                if reminder_date_str and status != self.STATUS_CLOSED:
                    try:
                        reminder_date = datetime.strptime(reminder_date_str, '%Y-%m-%d').date()
                        if reminder_date <= today:
                            followup_leads.append(lead)
                    except ValueError:
                        pass

            return followup_leads

        except Exception as e:
            logger.error(f"Error getting follow-up leads: {str(e)}")
            return []

    def get_statistics(self) -> Dict:
        """Get lead statistics"""
        try:
            leads = self.get_all_leads()

            stats = {
                'total_leads': len(leads),
                'new_leads': sum(1 for l in leads if l.get('status') == self.STATUS_NEW),
                'in_conversation': sum(1 for l in leads if l.get('status') == self.STATUS_IN_CONVERSATION),
                'calls_scheduled': sum(1 for l in leads if l.get('status') == self.STATUS_CALL_SCHEDULED),
                'closed': sum(1 for l in leads if l.get('status') == self.STATUS_CLOSED),
                'not_suitable': sum(1 for l in leads if l.get('status') == self.STATUS_NOT_SUITABLE),
                'avg_match_score': 0,
                'high_quality_leads': 0,
            }

            if leads:
                scores = []
                for lead in leads:
                    try:
                        score = int(lead.get('match_score', 0))
                        scores.append(score)
                        if score >= 70:
                            stats['high_quality_leads'] += 1
                    except (ValueError, TypeError):
                        pass

                if scores:
                    stats['avg_match_score'] = sum(scores) / len(scores)

            return stats

        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {}
