############################### AFFILIATE DEMOGRAPHIC FUNCTIONS##########################################
# The DB is currenty djangos models cause that's what i started with, it'll be changed eventually and the models will be sent to a postgres database
# Research says its easy to do - so i'll do that later
def get_chart_data(affiliates, field):
    chart_data = (
        affiliates.values(field)
        .annotate(count=Count(field))
        .order_by(field)
    )
    return {'labels': [entry[field] for entry in chart_data], 'counts': [entry['count'] for entry in chart_data]}

def get_student_type_data(affiliates):
    student_type_data = (
        affiliates.values('undergraduate')
        .annotate(count=Count('undergraduate'))
    )
    return [entry['count'] for entry in student_type_data]

def get_new_affiliates_data(affiliates):
    new_affiliates_data = (
        affiliates.annotate(
            week=ExtractWeek('joined'),
            year=ExtractYear('joined')
        )
        .values('week', 'year')
        .annotate(count=Count('id'))
        .order_by('year', 'week')
    )
    return {'labels': [f"Week {entry['week']}, {entry['year']}" for entry in new_affiliates_data], 
            'counts': [entry['count'] for entry in new_affiliates_data]}

def get_top_chart_data(affiliates, field):
    top_chart_data = (
        affiliates.exclude(**{f"{field}__isnull": True})  # Exclude entries where field is None
        .values(field)
        .annotate(count=Count(field))
        .order_by('-count')[:5]
    )
    return {'labels': [entry[field] for entry in top_chart_data], 'counts': [entry['count'] for entry in top_chart_data]}

########################################## AFFILIATE GROUPS LINE & PIE CHART FUNCTIONS ##########################################################

def get_monthly_sales_by_field(field_name):
    # Validate the field name
    try:
        Affiliate._meta.get_field(field_name)
    except FieldDoesNotExist:
        raise ValueError(f"Invalid field name: {field_name}")

    # Query the Sales model, annotate with month and year, and group by the specified field
    sales_data = Sales.objects.annotate(
        month=TruncMonth('start_date'),
        year=ExtractYear('start_date'),
        affiliate_field_value=Subquery(
            Affiliate.objects.filter(
                id=OuterRef('ticket__affiliate__id')
            ).values(field_name)
        )
    ).values('affiliate_field_value', 'month', 'year').annotate(total_sales=Count('id'))

    # Convert the query results to a pandas DataFrame
    sales_df = pd.DataFrame(sales_data)

    try:
        # Pivot the data to create a wide format DataFrame
        pivot_data = sales_df.pivot_table(
            index='affiliate_field_value',
            columns=['year', 'month'],
            values='total_sales',
            aggfunc='sum',
            fill_value=0
        ).sort_index()

        # Convert the DataFrame back to a format suitable for Chart.js
        data = {}
        labels = []
        for index, row in pivot_data.iterrows():
            data[index] = {
                'label': {True: "Undergrad", False: "Grad"}.get(index, str(index)),
                'data': [row[year, month] for year, month in sorted(row.index)]
            }

            if not row.empty:
                labels = [month_name[month.month] + ' ' + str(year) for year, month in sorted(row.index)]
    except:
        curr_year = datetime.today().year
        labels = [f"{calendar.month_name[month]} {curr_year}" for month in range(1, 13)]
        default_data = [
            {'label': f"{month} {year}", 'data': [0] * len(labels)}
            for i, label in enumerate(labels)
            for month, year in [label.split()]
        ]
        data = {f"Default Label {i}": value for i, value in enumerate(default_data, start=1)}
    # Query to count the number of tickets for each field value
    affiliates_data = Affiliate.objects.exclude(**{f"{field_name}__isnull": True}).values(field_name).annotate(
    total_affiliates=Count('id', distinct=True),
    total_tickets=Count('tickets__affiliate__id', distinct=True)
    )

    # Calculate conversion rates
    convdata = {}
    for entry in affiliates_data:
        field_value = entry[field_name]
        total_affiliates = entry['total_affiliates']
        total_tickets = entry['total_tickets']
        conversion_rate = round((total_tickets / total_affiliates) * 100, 2) if total_affiliates > 0 else 0
        convdata[field_value] = {
            'total_affiliates': total_affiliates,
            'total_tickets': total_tickets,
            'conversion_rate': conversion_rate,
            'value': 'Undergraduate' if field_value is True else 'Graduate' if field_value is False else field_value
        }

    return {
        'labels': labels,
        'datasets': list(data.values()),
        'conversion_rates': json.dumps(list(convdata.values()), cls=DjangoJSONEncoder)
    }
