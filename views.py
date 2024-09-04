def message_affiliates(request):
    if request.method == 'POST':
        try:
            if request.POST.get('message_type') == 'announcement':
                subject = f"Announcement! :{request.POST.get('subject')}"
                template='announcement'
            else:
                subject = f"Important! :{request.POST.get('subject')}"
                template='informational'
            body = request.POST.get('body')
            # Initialize an empty list to store each line
            lines = []
            # Split the post_body by lines
            lines = body.splitlines()
            gender = request.POST.get('gender')
            undergraduate = request.POST.get('is_undergraduate')

            # Build the filter conditions
            filters = Q()
            if gender and gender != '':
                filters &= Q(gender=gender)
            if undergraduate:
                filters &= Q(undergraduate=True)

            # Get all filtered affiliates emails
            recipient = list(Affiliate.objects.filter(filters).values_list('email', flat=True))
            # Get the list of uploaded files
            uploaded_files = request.FILES.getlist('images')
            image_path = []
            if uploaded_files:
                target_dir = 'writer/static/images/sent_images/'
                name = 0
                for uploaded_file in uploaded_files:
                    # Generate a unique file name
                    file_name = f"{name}_{uploaded_file.name}"
                    file_path = f"{target_dir}{file_name}"
                    # Save the file to the directory
                    with open(file_path, 'wb+') as destination:
                        for chunk in uploaded_file.chunks():
                            destination.write(chunk)
                    image_path.append(file_path)
                    name+= 1
            content = {
                'lines': lines
                }           
            send_email(recipient, subject, content, template, body, image_path)
            messages.success(request, 'Message sent successfully!', extra_tags='sale')
        except Exception as e:
            messages.info(request, f'Unable to send message: {str(e)}', extra_tags='sale')

    return redirect('writer:index')

def sales_chart(request):
    # Fetch referred and non-referred sales data grouped by month
    sales_data = Sales.objects.annotate(
        month=TruncMonth('start_date'),  # Extract month from start_date
        is_referred=Case(  # Define a boolean field indicating if sale is referred or not
            When(referred=True, then=Value(True, output_field=BooleanField())),  # If referred is True
            When(referred=False, then=Value(False, output_field=BooleanField())),  # If referred is False
            default=Value(False, output_field=BooleanField()),  # Default to False
            output_field=BooleanField()  # Output field type
        ),
        aff_fee=Sum(Subquery(
            Ticket.objects.filter(
                id=OuterRef('ticket_id')
            ).values('affiliate_earning'))
        ),
        total_amount=Sum(Case(  # Calculate total_amount taking into account affiliate fee for referred sales
            When(referred=True, then=F('agreed_price') - Subquery(Ticket.objects.filter(id=OuterRef('ticket_id')).values('affiliate_earning')[:1])),  # For referred sales
            default=F('agreed_price'),  # For non-referred sales
            output_field=IntegerField()  # Output field type
        ))
    ).values('month', 'is_referred', 'aff_fee', 'total_amount').annotate(
        sales_count=Count('id'),  # Count the number of sales
        sales_amount=Sum('agreed_price')  # Sum the agreed prices for total sales amount
    ).order_by('month')
    # Retrieve Data from the Model
    affiliates = Affiliate.objects.all()

    # Process Affiliate Data
    hear_about_us_data = get_chart_data(affiliates, 'hear_about_us')
    gender_data = get_chart_data(affiliates, 'gender')
    student_type_data = get_student_type_data(affiliates)
    new_affiliates_data = get_new_affiliates_data(affiliates)
    university_data = get_top_chart_data(affiliates, 'university')
    department_data = get_top_chart_data(affiliates, 'department')
    # Process Affiliate Group Sales Data
    gender_line_data = get_monthly_sales_by_field('gender')
    hear_about_us_line_data = get_monthly_sales_by_field('hear_about_us')
    undergraduate_line_data = get_monthly_sales_by_field('undergraduate')
    university_line_data = get_monthly_sales_by_field('university')
    department_line_data = get_monthly_sales_by_field('department')
    # Serialize the data into JSON format
    sales_data_json = json.dumps(list(sales_data), cls=DjangoJSONEncoder)

    # Client sales data (universities and departments i've sold to)
    university_sales = Universities.objects.annotate(total_sales=Count('sales')).values('name', 'total_sales').order_by('-total_sales')
    department_sales = Departments.objects.annotate(total_sales=Count('sales')).values('name', 'total_sales').order_by('-total_sales')

    context = {
        # Pass serialized data to the template
        'sales_data_json': sales_data_json,
        'hear_about_us_labels': hear_about_us_data['labels'],
        'hear_about_us_counts': hear_about_us_data['counts'],
        'gender_labels': gender_data['labels'],
        'gender_counts': gender_data['counts'],
        'student_type_labels': ['Undergraduate', 'Graduate'],
        'student_type_counts': student_type_data,
        'new_affiliates_labels': new_affiliates_data['labels'],
        'new_affiliates_counts': new_affiliates_data['counts'],
        'university_labels': university_data['labels'],
        'university_counts': university_data['counts'],
        'department_labels': department_data['labels'],
        'department_counts': department_data['counts'],
        'gender_line_data': gender_line_data,
        'hear_about_us_line_data': hear_about_us_line_data,
        'undergraduate_line_data': undergraduate_line_data,
        'university_line_data': university_line_data,
        'department_line_data': department_line_data,
        'client_university_data': json.dumps(list(university_sales), cls=DjangoJSONEncoder),
        'client_department_data': json.dumps(list(department_sales), cls=DjangoJSONEncoder),
    }

    return render(request, 'writer/sales_chart.html', context)

def university_sales_view(request):
    # Get the university name from the query parameter
    search_university = request.GET.get('university', '')
    # Get all universities with their departments and sales count
    university_data = Universities.objects.annotate(
        total_sales=Count('sales')
    ).prefetch_related(
        'sales__department'
    ).order_by('-total_sales')

    # Prepare data for the template
    university_charts_data = []
    for university in university_data:
        department_data = university.sales.values('department__name').annotate(
            total_sales=Count('id')
        ).order_by('-total_sales')

        university_charts_data.append({
            'name': university.name,
            'total_sales': university.total_sales,
            'departments': list(department_data)
        })

    context = {
        'university_charts_data': university_charts_data,
        'search_university': search_university 
    }

    return render(request, 'writer/university_sales.html', context)

def view_ticket(request):
    query = request.GET.get('q')
    results = None
    result = None
    path = None
    receipt = None
    # Perform search for ticket id
    if query:
        results = Ticket.objects.filter(id=query).first()
    if results:
        result = Sales.objects.filter(ticket=results.id).first()
        path = f"{results.affiliate.full_name.split()[0]}_ticket({results.id}).png"
        receipt = str(results.confirmed_receipt).replace('writer/static/images/', '', 1)
    context = {
        'results': results,
        'sale': result,
        'path': path,
        'receipt': receipt,
        'search_performed': bool(query)  # Indicates whether a search has been performed
    }
    return render(request, 'writer/view_ticket.html', context)

def search_voucher(request):
    image_url = None

    if request.method == 'GET':
        query = request.GET.get('q', '').capitalize()

        # Directory to search for images
        search_dir = 'writer/static/KL_VTU_vouchers'

        # Search for the image in the specified directory
        if os.path.exists(search_dir):
            for filename in os.listdir(search_dir):
                if query in filename.capitalize():
                    image_url = filename
                    break

    context = {
        'image_url': image_url,
        'search_performed': bool(query),
    }
    return render(request, 'writer/vouchers.html', context)

def delete_voucher(request, filename):
    voucher_path = f'writer/static/KL_VTU_vouchers/{filename}'
    if os.path.exists(voucher_path):
        os.remove(voucher_path)
        messages.success(request, "Voucher removed successfully!", extra_tags='sale')
    return redirect('writer:search_voucher')

def resend_emails(request):
    directory_path = 'writer/static/failed_emails/'
    check_directory_path = 'writer/static/check/'
    # Get a list of filenames in the directory
    filenames = os.listdir(directory_path)
    # Create a dictionary to pass to the template
    context = {'files': filenames}
    if request.method == 'GET' and 'file_name' in request.GET:
        file_name = request.GET['file_name']
        file_path = os.path.join(directory_path, file_name)
        with open(file_path, 'rb') as f:
            recipients, messagez = pickle.load(f)
        auto_send(recipients, messagez)
        check_file_path = os.path.join(check_directory_path, file_name)
        shutil.move(file_path, check_file_path)

        messages.success(request, "Emails are Resending...", extra_tags='sale')
    return render(request, 'writer/resend.html', context)
