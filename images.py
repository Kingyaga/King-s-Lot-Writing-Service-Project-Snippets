# Function to issue a ticket
def issue_ticket(affiliate_obj, client_name, agreed_price):
    # Open the ticket template image
    image = Image.open("writer/static/images/W.S Affiliate Transaction Ticket.png")

    # Create a drawing object
    draw = ImageDraw.Draw(image)

    # Load the font
    font = ImageFont.truetype("writer/static/fonts/Montserrat-Bold.ttf", 45)
    price_font = ImageFont.truetype("writer/static/fonts/Montserrat-Bold.ttf", 66)
    tag_font = ImageFont.truetype("writer/static/fonts/Montserrat-Bold.ttf", 30)
    date_font = ImageFont.truetype("writer/static/fonts/Montserrat-Regular.ttf", 31)

    # Set the text positions
    tag_position = (225, 48)  # (x, y) coordinates
    client_name_position = (450, 130)
    agreed_price_position = (900, 215)
    aff_fee_position = (945, 340)
    sdate_position = (66, 205)
    ticket_ref_no_position = (1400, 575)

    # Calculate the affiliate fee
    aff_fee = agreed_price
    if aff_fee > 55000:
        aff_fee -= 30000
    else:
        aff_fee -= 25000

    # Get today's date
    today = datetime.today()
    # Format today's date as dd/mm/yy
    formatted_sdate = today.strftime("%d/%m/%y")

    # Create the ticket
    ticket = Ticket.objects.create(
        affiliate=affiliate_obj,
        affiliate_earning=aff_fee
    )
    ticket.save()
    # Generate the ticket reference number
    ticket_ref_no = f"dis_issa_secret"

    # Draw the data on the image
    draw.text(tag_position, str(affiliate_obj.id), font=tag_font, fill="#2F0E11") 
    draw.text(client_name_position, client_name.title(), font=font, fill="#2F0E11")
    draw.text(agreed_price_position, "{:,}".format(agreed_price), font=price_font, fill="#F9EFE0")
    draw.text(aff_fee_position, "{:,}".format(aff_fee), font=price_font, fill="#F9EFE0")
    draw.text(sdate_position, formatted_sdate, font=date_font, fill="#F9EFE0") 
    draw.text(ticket_ref_no_position, ticket_ref_no, font=font, fill="#F9EFE0") 

    # Save the ticket
    name = affiliate_obj.full_name.split()[0]
    # Save the image with the ticket number
    image.save(f"writer/static/tickets/open_tickets/{name}_ticket({ticket.id}).png")
    return ticket

# Function to close a ticket
def close_ticket(request, name, id):
    try:
        # Open the ticket template image
        file_name = f"writer/static/tickets/open_tickets/{name}_ticket({id}).png"
        image = Image.open(file_name)
        # Create a drawing object
        draw = ImageDraw.Draw(image)
        # Load the font
        date_font = ImageFont.truetype("writer/static/fonts/Montserrat-Regular.ttf", 31)
        end_font = ImageFont.truetype("writer/static/fonts/BrittanySignature.ttf", 200)
        # Set the text positions
        edate_position = (66, 315)
        end_position = (250, 250)

        end = 'CLOSED'
        # Get today's date
        today = datetime.today()
        # Format today's date as dd/mm/yy
        formatted_edate = today.strftime("%d/%m/%y")
        # Draw the data on the image
        draw.text(edate_position, formatted_edate, font=date_font, fill="#F9EFE0") 
        draw.text(end_position, end, font=end_font, fill="#FFFFFF")
        # Save the image with the ticket number
        image.save(f"writer/static/tickets/closed_tickets/{name}_ticket({id}).png")
        messages.success(request, "Ticket closed successfully!", extra_tags='sale')
    except Exception as e:
        messages.info(request, f"An error occurred while closing the ticket: '{e}'", extra_tags='sale')
        return None
    return file_name

# cropping screenshoted data for an auto-mail
def screenshot(image_data, option):        
    # Remove the data URL prefix
    image_data = image_data.replace('data:image/png;base64,', '')
    
    # Decode the base64 string
    image_bytes = base64.b64decode(image_data)
    # Open the image using PIL
    screenshot = Image.open(io.BytesIO(image_bytes))
    output_buffer = io.BytesIO()
    width, height = screenshot.size
    if option == 'activate':
        screenshot = screenshot.crop((0, 0, width, height - 80))
        # Open the overlay image
        overlay = Image.open("writer/static/images/activated_stamp.png")

        # Ensure the overlay has an alpha channel
        if overlay.mode != 'RGBA':
            overlay = overlay.convert('RGBA')
        # Rotate the overlay (e.g., 45 degrees)
        overlay = overlay.rotate(45, expand=True)
        # Calculate position to center the overlay horizontally at the bottom
        x_position = (screenshot.width - overlay.width) // 2
        y_position = screenshot.height - overlay.height
        # Create a new image with the same size as the screenshot
        new_image = Image.new('RGBA', screenshot.size, (0, 0, 0, 0))
        # Paste the screenshot
        new_image.paste(screenshot, (0, 0))
        # Paste the overlay
        new_image.paste(overlay, (x_position, y_position), overlay)
        # Save the result
        new_image.save(output_buffer, format='PNG')
    else:
        screenshot.save(output_buffer, format='PNG')

    # Save the file
    file_name = f"writer/static/images/email/screenshot.png"
    with open(file_name, 'wb') as f:
        f.write(output_buffer.getvalue())
    return file_name
