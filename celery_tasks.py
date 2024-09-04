from django.core.mail import get_connection, EmailMultiAlternatives
from kings_lot_WS.settings import EMAIL_HOST_USER, CELERY_BROKER_URL
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.http import MediaIoBaseDownload
from django.template.loader import render_to_string
from celery.exceptions import SoftTimeLimitExceeded
from email.mime.application import MIMEApplication
from googleapiclient.discovery import build
from google.oauth2 import service_account
from .models import Affiliate, Promotion
from django.core.mail import send_mail
from email.mime.image import MIMEImage
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from celery import shared_task
from datetime import datetime
from pathlib import Path
import subprocess
import mimetypes
import gspread
import logging
import pickle
import random
import os
import io
import re


# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

############################################ Functions that handle sending emails ####################################################################################

## Notify affiliate about pending payment via whatsapp
## Automating this with whatsapp would be better but the process only works with whatsap web, i'll do more research and see how this can be improved but till then this will serve
@shared_task
def notify(notification, send):
    try:
        # Use regex to extract the number and the rest of the string
        match = re.match(r'^(\+?[0-9]+),(.*)$', notification, re.DOTALL)
        if match:
            full_number = match.group(1)  # This is the full number
            subject = full_number[3:]  # Remove first 3 digits (this is the code to search on whatsapp)
            body = match.group(2)
        else:
            raise Exception("Invalid data format: expected number followed by comma and message")    
        send_mail(
            subject=subject, # Whatsapp code
            message=body,
            from_email=EMAIL_HOST_USER,
            recipient_list=[send],  # Sending to myself, copy then send notification to affiliate on whatsapp
            fail_silently=False,
        )
    except Exception as e:
        print(f"Something went wrong!: {str(e)}")
    return

# List of email templates that require the 'kings_lot_vtu' image attachment
vtu =[
    "announcement",
    "birthday_gift",
    "final_year",
    "graduated",
    "informational",
    "rank1",
    "rank2",
    "refer500",
    "refer1000",
    "promotion_start",
    "promotion_end",
    "payout",
    "activated",
    "denied"
]

# Helper function to encode images for inline display in emails
# base64 will be a more ideal approach, figure it out and implement
@shared_task
def encode(temp):
    img_path = f"writer/static/images/email/{temp}.png"
    with open(img_path, "rb") as img_file:
        mime_type, _ = mimetypes.guess_type(img_path)
        attachment = MIMEImage(img_file.read(), _subtype=mime_type.split('/')[-1])
        if 'refer_' in img_path:
            temp = ''.join([char for char in temp if not char.isdigit()])
        cid = f"<{temp}_cid>"
        attachment.add_header('Content-ID', cid)
        attachment.add_header('Content-Disposition', 'inline')
    return(attachment)

# Email error handler code
# Catch failed emails- network might be having issues and catching these are essntial cause they're automated, the module being named 'pickle' is just hillarious
def handle_failed_emails(recipient_emails, messagez, exception):
    failed_emails_dir = os.path.join('writer', 'static', 'failed_emails')
    failed_emails_file = os.path.join(failed_emails_dir, f'failed_emails_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pickle')
    os.makedirs(failed_emails_dir, exist_ok=True)
    with open(failed_emails_file, 'wb') as f:
        pickle.dump((recipient_emails, messagez), f)
    # Log the failure
    logger.error(f"Failed to send emails, please retry. Exception: {exception}")
    return

# Task to prepare and send email batches
# For automails that go to many emails
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3}, broker=CELERY_BROKER_URL)
def prepare_email_task(self, recipient_emails, messagez):
    connection = get_connection()
    try:
        connection.open()

        email_batches = []
        batch_size = 50
        email_messages = []

        for recipient, message_data in zip(recipient_emails, messagez):
            if len(message_data) == 4:
                subject, template, content, alternative = message_data
                image_paths = []
            else:
                subject, template, content, alternative, image_paths = message_data

            email = EmailMultiAlternatives(
                subject=subject,
                body=alternative,
                from_email=EMAIL_HOST_USER,
                to=[recipient],
            )
            html_content = render_to_string(f'email/{template}.html', content)
            email.attach_alternative(html_content, 'text/html')

            # Attach image files as attachments
            for image_path in image_paths:
                if "screenshot" in image_path:
                    email.attach(encode("screenshot"))
                    continue
                try:
                    with open(image_path, "rb") as img_file:
                        image_binary_content = img_file.read()
                        image_filename = Path(image_path).name
                        if image_filename.lower().endswith('.pdf'):
                            mime_image = MIMEApplication(image_binary_content, _subtype='pdf')
                        else:
                            mime_image = MIMEImage(image_binary_content)
                        content_disposition = f"attachment; filename={image_filename}"
                        mime_image.add_header("Content-Disposition", content_disposition)
                        email.attach(mime_image)
                except Exception:
                    pass

            # Attach inline images
            if template in vtu:
                email.attach(encode('kings_lot_vtu'))
            if 'refer_' in template:
                email.attach(encode(f"{template}{random.randint(1, 11)}"))
                email.attach(encode('kings_lot_vtu'))
            else:
                email.attach(encode(template))
            email.attach(encode('whatsapp'))
            email.attach(encode('klws_silv'))

            email_messages.append(email)

            if len(email_messages) == batch_size:
                email_batches.append(email_messages)
                email_messages = []

        if email_messages:
            email_batches.append(email_messages)

        # Send email batches and retry if there's an exception
        for email_batch in email_batches:
            try:
                connection.send_messages(email_batch)
            except (Exception, SoftTimeLimitExceeded) as e:
                try:
                    # Log the failure
                    logger.info(f"Something went wrong, retrying now: attempts-{self.request.retries}....")            
                    # Retry with a delay
                    self.retry(exc=e, countdown= 10 ** self.request.retries)
                except:
                    # Write failed emails to a file if max retries are exhausted
                    if self.request.retries == self.max_retries:
                        handle_failed_emails(recipient_emails, messagez, e)
                        return
            finally:
                connection.close()

    except (Exception, SoftTimeLimitExceeded) as e:
        try:
            # Log the failure
            logger.info(f"Something went wrong, retrying now: attempts-{self.request.retries}....")            
            # Retry with a delay
            self.retry(exc=e, countdown= 10 ** self.request.retries)
        except:
            # Write failed emails to a file if max retries are exhausted
            if self.request.retries == self.max_retries:
                handle_failed_emails(recipient_emails, messagez, e)
                return

# Task to send individual emails
# automails for individuals function - i think one email sending function would be best tbh
@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3}, broker=CELERY_BROKER_URL)
def send_email_task(self, recipient_emails, subject, content, template, alternative, image_paths=[]):
    connection = get_connection()
    messagez = []
    try:
        connection.open()

        # Split recipient_emails into chunks of 50
        for i in range(0, len(recipient_emails), 50):
            chunk = recipient_emails[i:i + 50]
            email_messages = []

            for recipient in chunk:
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=alternative,
                    from_email=EMAIL_HOST_USER,
                    to=[recipient],
                )
                html_content = render_to_string(f'email/{template}.html', content)
                email.attach_alternative(html_content, 'text/html')

                # Attach image files as attachments
                for image_path in image_paths:
                    try:
                        with open(image_path, "rb") as img_file:
                            image_binary_content = img_file.read()
                            mime_image = MIMEImage(image_binary_content)
                            image_filename = Path(image_path).name
                            content_disposition = f"attachment; filename={image_filename}"
                            mime_image.add_header("Content-Disposition", content_disposition)
                            email.attach(mime_image)
                    except Exception:
                        pass
                    
                # Attach inline images
                email.attach(encode(template))
                email.attach(encode('whatsapp'))
                email.attach(encode('klws_silv'))
                if template in vtu:
                    email.attach(encode('kings_lot_vtu'))
                email_messages.append(email)

            try:
                connection.send_messages(email_messages)  
            except (Exception, SoftTimeLimitExceeded) as e:
                try:
                    # Log the failure
                    logger.info(f"Something went wrong, retrying now: attempts-{self.request.retries}....")
                    # Retry with a delay
                    self.retry(exc=e, countdown= 10 ** self.request.retries)
                except:
                    # Write failed emails to a file if max retries are exhausted
                    if self.request.retries == self.max_retries:
                        for recipient in recipient_emails:
                            messagez.append((subject, content, template, alternative, image_paths))
                        handle_failed_emails(recipient_emails, messagez, e)   
                    return
            finally:
                email_messages.clear()  # Clear the list for the next chunk of emails
        connection.close()

    except (Exception, SoftTimeLimitExceeded) as e:
        try:
            # Log the failure
            logger.info(f"Something went wrong, retrying now: attempts-{self.request.retries}....")
            # Retry with a delay
            self.retry(exc=e, countdown= 10 ** self.request.retries)
        except:
            # Write failed emails to a file if max retries are exhausted
            if self.request.retries == self.max_retries:
                for recipient in recipient_emails:
                    messagez.append((subject, content, template, alternative, image_paths))
                handle_failed_emails(recipient_emails, messagez, e)
            return
        
###########################################################################################################################################################        

######################################################### Functions that use Google sheets ################################################################

# Constants
# Set up paths and ids and stuff
CREDENTIALS_FILE = r"C:\Users\Owner\Documents\BINCOM_SCHOLARSHIP\BINCOM_SCHOLARSHIP\KLWS\kings_lot_WS\writer\static\kings-lot-ws-7e99e1bc2b2d.json"
REPO_PATH = r"C:\Users\Owner\Documents\Backup_King's lot stuff\KLWS_Affiliate_Resources"
SALE_LOGS_PATH = os.path.join(REPO_PATH, "Sales_Logs", "affiliate_logs")
PROMO_LOGS_PATH = os.path.join(REPO_PATH, "Promotion_Logs", "affiliate_logs")
APRL_SPREADSHEET_ID = "dis_issa_secret"
CONTACT_SPREADSHEET_ID = "dis_issa_secret"
ASH_SPREADSHEET_ID = "dis_issa_secret"
# this is my attempt to make the sheet data extraction faster, by bookmarking last read parts
TRACKER_FILE = 'writer/static/last_processed_row.txt'

# Helper Functions for the little things
def referral(value):
    try:
        return int(value.split(' - ')[1])
    except:
        return 0

def return_none_if_empty(value):
    """Return None if the string is empty, otherwise return the string."""
    return None if not value else value

def remove_trailing_zeros(num):
    """Remove trailing zeros"""
    return int(str(num).rstrip('0')) if num != None else None

def convert_yes_no_to_bool(value):
    """Convert 'yes' or 'no' string to boolean."""
    return value.lower() == "yes"

def convert_timestamp(timestamp_str):
    """Convert a timestamp string to a datetime object"""
    try:
        # Try to parse the timestamp string with time
        value = datetime.strptime(timestamp_str, '%m/%d/%Y %H:%M:%S')
        # Convert the naive datetime to timezone-aware datetime
        converted_value = timezone.make_aware(value, timezone.get_current_timezone()).date()
    except ValueError:
        try:
            # If that fails, try to parse without time
            converted_value = datetime.strptime(timestamp_str, '%m/%d/%Y')
        except ValueError:
            # If both formats fail, set converted_value to None
            converted_value = None
    return converted_value
        
def get_sheet(spreadsheet_id):
    """Authenticate and return the specified Google Sheet."""
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(spreadsheet_id).sheet1

def get_last_processed_row(spreadsheet_id):
    """Get the last processed row for a specific spreadsheet."""
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, 'r') as f:
            for line in f:
                if line.startswith(spreadsheet_id):
                    return int(line.split(':')[1])
    return 1

def update_last_processed_row(spreadsheet_id, row):
    """Update the last processed row for a specific spreadsheet."""
    lines = []
    updated = False

    # Read existing content if file exists
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE, 'r') as f:
            lines = f.readlines()

    # Update or add the new row
    with open(TRACKER_FILE, 'w') as f:
        for line in lines:
            if line.startswith(f"{spreadsheet_id}:"):
                f.write(f"{spreadsheet_id}:{row}\n")
                updated = True
            else:
                f.write(line)
        if not updated:
            f.write(f"{spreadsheet_id}:{row}\n")

def get_drive_service():
    """Create and return an authorized Drive service instance."""
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/spreadsheets.readonly']
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def process_screenshots(file_ids, formatted_date, screenshots_dir, affiliate_dir, drive_service):
    """
    Process and save screenshots, returning a list of markdown-formatted image links.
    
    Args:
    file_ids (list): List of Google Drive file IDs for the screenshots.
    formatted_date (str): Formatted date string to use in the filename.
    screenshots_dir (str): Directory to save the screenshots.
    affiliate_dir (str): Base directory of the affiliate's logs.
    drive_service: Google Drive service object for downloading files.
    
    Returns:
    list: List of markdown-formatted image links.
    """
    image_links = []
    for index, file_id in enumerate(file_ids, start=1):
        image_filename = f"{formatted_date}_screenshot_{index}.jpg"
        image_path = os.path.join(screenshots_dir, image_filename)
        download_and_save_image(drive_service, file_id, image_path)
        relative_image_path = os.path.relpath(image_path, start=os.path.dirname(affiliate_dir)).replace('\\', '/')
        image_links.append(f"[{image_filename}]({relative_image_path})\n")
    return image_links

def download_and_save_image(service, file_id, save_path):
    """Download an image from Google Drive and save it locally."""
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    fh.seek(0)
    with open(save_path, 'wb') as f:
        f.write(fh.read())

def extract_file_ids(text):
    """Extract Google Drive file IDs from a given text."""
    pattern = r"(?:open\?id=|/file/d/)([a-zA-Z0-9_-]+)"
    return re.findall(pattern, text)

# Automatically send files to git after reading them from the spreadseet and writing them. What a very lazy but time-saving thing to do
def update_git_repo():
    if not os.path.isdir(REPO_PATH):
        print(f"Error: Invalid repository path: {REPO_PATH}")
        return False

    def git_cmd(command):
        return subprocess.run(command, cwd=REPO_PATH, capture_output=True, text=True, check=False)

    git_cmd(["git", "fetch", "origin"])
    git_cmd(["git", "add", "."])

    if git_cmd(["git", "diff", "--staged", "--quiet"]).returncode == 0:
        print("No changes to commit.")

    commit = git_cmd(["git", "commit", "-m", "Updated new logs today"])
    if "nothing to commit" in commit.stderr:
        print("Repository is up-to-date.")

    def push():
        return git_cmd(["git", "push", "origin", "main"])

    push_result = push()
    if push_result.returncode != 0 and "non-fast-forward" in push_result.stderr:
        print("Push rejected. Attempting to pull changes and retry...")
        if git_cmd(["git", "pull", "--rebase", "origin", "main"]).returncode == 0:
            if push().returncode == 0:
                print("Pull and push successful after retry.")
                return True
        print("Failed to push even after pulling. Manual intervention may be required.")
        return False

    if push_result.returncode != 0:
        print(f"Git push failed: {push_result.stderr}")
        return False

    print("Repository updated successfully.")
    return True

def get_batch_records(sheet, start_row, batch_size):
    end_row = start_row + batch_size
    
    # Get the headers from the first row
    headers = sheet.row_values(1)
    
    # Get the data for the specified range, starting from the row after the headers
    data = sheet.get(f'A{start_row + 1}:Z{end_row}')
    
    records = []
    for row in data:
        if any(row):  # Check if row is not entirely empty
            # Pad the row with empty strings if it's shorter than headers
            padded_row = row + [''] * (len(headers) - len(row))
            record = dict(zip(headers, padded_row))
            records.append(record)
    
    return records

def create_affiliate(record):
    return Affiliate(
        joined=convert_timestamp(record['Timestamp']),
        full_name=record['Full name'],
        gender=record['Gender'],
        date_of_birth=convert_timestamp(record['Date of Birth']),
        email=record['Email'],
        phone_number=record['Phone Number'],
        hear_about_us=record['How did you hear about us?'],
        bank_name=record['Bank Name'],
        account_number=record['Account Number'],
        account_name=record['Name on the account.'],
        undergraduate=convert_yes_no_to_bool(record['Are you an undergraduate?']),
        university=return_none_if_empty(record['University']),
        department=return_none_if_empty(record['Department']),
        level=remove_trailing_zeros(return_none_if_empty(record['Level'])),
        course_duration=return_none_if_empty(record['How many years is your course?'])
    )

def process_aprl_record(record, drive_service):
    tag = record['Your affiliate tag']
    try:
        affiliate = Promotion.objects.get(affiliate=referral(tag))
        if affiliate.affiliate.full_name.split()[0].lower() != tag.split(' - ')[0].lower():
            print(f"Affiliate tag '{tag}' not valid")
            return
    except:
        # Skip if tag is not found
        print("Affiliate doesn't have a promotion instance")
        return
    # Extract file IDs and process images
    conversation_summary = record['Upload screenshots of your message, conversation or post (if available)']
    file_ids = extract_file_ids(conversation_summary) if conversation_summary else []
    # Create directories
    affiliate_dir = os.path.join(PROMO_LOGS_PATH, tag.replace(" - ", "_"))
    os.makedirs(affiliate_dir, exist_ok=True)
    screenshots_dir = os.path.join(affiliate_dir, 'screenshots')
    os.makedirs(screenshots_dir, exist_ok=True)
    # Process timestamp and prepare data
    timestamp = datetime.strptime(record['Timestamp'], '%m/%d/%Y %H:%M:%S')
    formatted_date = timestamp.strftime('%Y-%m-%d-%H%M%S')
    # Download and process images
    image_links = process_screenshots(file_ids, formatted_date, screenshots_dir, affiliate_dir, drive_service)
    # Prepare data for markdown file
    data = {
        'date': formatted_date,
        'affiliate_tag': tag,
        'referral_count': affiliate.referral_count,
        'who_did_you_refer': [ref.strip() for ref in record['Who did you refer?'].split(',')],
        'brief_description': record['Briefly describe what you did'],
        'referral_methods': [method.strip() for method in record['How did YOU make these referrals?'].split(',')],
        'specific_message': record['What specific message did you use for the referral?'],
        'conversation_summary': image_links if image_links else ["No screenshot provided"],
        'what_worked_best': [item.strip() for item in record['What parts of your referral worked best?'].split(',')],
        'why_they_signed_up': record['What do you think made them sign-up?'],
        'what_you_did_well': record['What did you do well when referring?'],
        'how_to_improve': record['How could you have done that better?']
    }
    # Write markdown file
    filename = f"{formatted_date}_submission.md"
    filepath = os.path.join(affiliate_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as file:
        # Write YAML front matter and markdown content
        file.write(f"""---
date: {data['date']}
affiliate_tag: {data['affiliate_tag']}
referral_count: {data['referral_count']}
---

# Referral Details

## Who did you refer?
{chr(10).join(f"- {ref}" for ref in data['who_did_you_refer'])}

## Brief description
{data['brief_description']}

## Referral methods
{chr(10).join(f"- {method}" for method in data['referral_methods'])}

## Specific message
{data['specific_message']}

## Screenshots
{chr(10).join(link for link in data['conversation_summary'])}

# Your Thoughts

## What worked best?
{chr(10).join(f"- {item}" for item in data['what_worked_best'])}

## Why they signed up
{data['why_they_signed_up']}

## What you did well
{data['what_you_did_well']}

## How to improve
{data['how_to_improve']}
""")

    pass

def process_ash_record(record, drive_service):
    tag = record['Your affiliate tag']
    try:
        affiliate = Affiliate.objects.get(id=referral(tag))
        if affiliate.full_name.split()[0].lower() != tag.split(' - ')[0].lower():
            print(f"Affiliate tag '{tag}' not valid")
            return
    except:
        # Skip if tag is not found
        print("Affiliate doesn't exist")
        return
    # Process timestamp and prepare data
    timestamp = datetime.strptime(record['Timestamp'], '%m/%d/%Y %H:%M:%S')
    formatted_date = timestamp.strftime('%Y-%m-%d-%H%M%S')
    
    # Create directories
    affiliate_dir = os.path.join(SALE_LOGS_PATH, tag.replace(" - ", "_"))
    os.makedirs(affiliate_dir, exist_ok=True)
    screenshots_dir = os.path.join(affiliate_dir, 'screenshots')
    os.makedirs(screenshots_dir, exist_ok=True)
    
    # Process screenshots
    conversation_summary = record['Upload screenshots of your message, conversation or post (if available, please remove any identifying information)']
    file_ids = extract_file_ids(conversation_summary) if conversation_summary else []
    # Download and process images
    image_links = process_screenshots(file_ids, formatted_date, screenshots_dir, affiliate_dir, drive_service)
    
    # Prepare data for markdown file
    data = {
        'date': formatted_date,
        'affiliate_tag': tag,
        'agreed_price': f"{int(record['What was the agreed price?']):,}",
        'client_type': record['Who was your client?'],
        'sale_duration': record['How long did the process take from first contact to closing the sale?'],
        'conversation_summary': record['What did you talk about?'],
        'screenshots': image_links if image_links else ["No screenshot provided"],
        'key_approach': record['What specific action or approach do you think made the biggest difference in closing this sale?'],
        'what_went_well': record['What did you do well in this sale?'],
        'future_improvements': record['Looking back, what would you do differently next time?'],
        'advice': record['What\'s one piece of advice you\'d give to other affiliates based on this experience?'],
        'company_support': record['Is there anything our company could provide to help you make more sales like this one?']
    }
    
    # Write markdown file
    filename = f"{formatted_date}_sale_submission.md"
    filepath = os.path.join(affiliate_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(f"""---
date: {data['date']}
affiliate_tag: {data['affiliate_tag']}
agreed_price: ₦{data['agreed_price']}
client_type: {data['client_type']}
sale_duration: {data['sale_duration']}
---

# Sale Details

## Who was your client?
{data['client_type']}

## Sale Duration
{data['sale_duration']}

## Agreed Price
₦{data['agreed_price']}

## Conversation Summary
{data['conversation_summary']}

## Screenshots
{chr(10).join(link for link in data['screenshots'])}

# Your Insights

## Key Approach
{data['key_approach']}

## What Went Well
{data['what_went_well']}

## Future Improvements
{data['future_improvements']}

## Advice for Other Affiliates
{data['advice']}

## How can King's Lot help you sell more?
{data['company_support']}
""")
    pass

@shared_task
def populate_from_sheets_task():
    sheet = get_sheet(CONTACT_SPREADSHEET_ID)
    last_row = get_last_processed_row(CONTACT_SPREADSHEET_ID)
    existing_emails = cache.get('existing_emails') or set(Affiliate.objects.values_list('email', flat=True))
    cache.set('existing_emails', existing_emails)
    
    batch_size = 100

    while True:
        try:
            records = get_batch_records(sheet, last_row, batch_size)
            if not records:
                break

            new_affiliates, new_promotions = [], []
            records_processed = 0
            
            for record in records:
                email = record.get('Email')
                if email and email not in existing_emails:
                    try:
                        affiliate = create_affiliate(record)
                        new_affiliates.append(affiliate)
                        new_promotions.append(Promotion(
                            affiliate=affiliate,
                            referred_by=referral(record.get('Referral Code', 0))
                        ))
                        existing_emails.add(email)
                    except Exception as e:
                        print(f"Error creating affiliate: {e}")
                        continue
                records_processed += 1
            
            with transaction.atomic():
                Affiliate.objects.bulk_create(new_affiliates)
                Promotion.objects.bulk_create(new_promotions)
            
            last_row += records_processed
            update_last_processed_row(CONTACT_SPREADSHEET_ID, last_row - 1)
            cache.set('existing_emails', existing_emails)
            
            if records_processed < batch_size:
                break  # We've reached the end of the data
        
        except Exception as e:
            print(f"Error processing batch: {e}")
            break
    
    return f"New affiliates : {records_processed}"

# this feels like a waste of lines, Aprl and Ash could be arguements to one function instead
@shared_task
def Aprl_populator_task():
    sheet = get_sheet(APRL_SPREADSHEET_ID)
    last_row = get_last_processed_row(APRL_SPREADSHEET_ID)
    drive_service = get_drive_service()
    batch_size = 100

    while True:
        records = get_batch_records(sheet, last_row, batch_size)
        if not records:
            break

        records_processed = 0
        for record in records:
            process_aprl_record(record, drive_service)
            records_processed += 1
        
        last_row += records_processed
        update_last_processed_row(APRL_SPREADSHEET_ID, last_row - 1)
        
        if records_processed < batch_size:
            break  # We've reached the end of the data

    update_git_repo()
    return f"New Promotion Entries : {records_processed}"

@shared_task
def Ash_populator_task():
    sheet = get_sheet(ASH_SPREADSHEET_ID)
    last_row = get_last_processed_row(ASH_SPREADSHEET_ID)
    drive_service = get_drive_service()
    batch_size = 100

    while True:
        records = get_batch_records(sheet, last_row, batch_size)
        if not records:
            break

        records_processed = 0
        for record in records:
            process_ash_record(record, drive_service)
            records_processed += 1
        
        last_row += records_processed
        update_last_processed_row(ASH_SPREADSHEET_ID, last_row - 1)
        
        if records_processed < batch_size:
            break  # We've reached the end of the data

    update_git_repo()
    return f"New Sales Entries : {records_processed - 1}"
