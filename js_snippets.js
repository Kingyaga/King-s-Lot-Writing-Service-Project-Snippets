document.addEventListener('DOMContentLoaded', () => {
    const forms = {
        affiliate: document.getElementById('affiliate_sale_form'),
        regular: document.getElementById('sale_form')
    };

    const requiredFields = {
        affiliate: [
            'affiliate_sale_project_topic',
            'affiliate_sale_client_name',
            'affiliate_sale_client_department',
            'affiliate_sale_client_university',
            'affiliate_sale_agreed_price',
            'autocompleteInput'
        ],
        regular: [
            'sale_project_topic',
            'sale_client_name',
            'sale_client_department',
            'sale_client_university',
            'sale_agreed_price'
        ]
    };

    const options = [];
    const schools = [];
    const departments = [];

    // Fetch options from Django views
    const fetchOptions = (url, targetArray) => {
        fetch(url)
            .then(response => response.json())
            .then(data => targetArray.push(...data))
            .catch(error => console.error(`Error fetching ${url}:`, error));
    };

    fetchOptions('/get-affiliate-options/', options);
    fetchOptions('/get-university-options/', schools);
    fetchOptions('/get-department-options/', departments);

    // Autocomplete setup
    const setupAutocomplete = (inputClass, suggestionsClass, dataArray) => {
        const inputs = document.getElementsByClassName(inputClass);
        const suggestionLists = document.getElementsByClassName(suggestionsClass);

        Array.from(inputs).forEach((input, index) => {
            const suggestions = suggestionLists[index];

            const updateSuggestions = () => {
                const inputValue = input.value.toLowerCase();
                const filteredOptions = dataArray.filter(option => option.toLowerCase().includes(inputValue));

                suggestions.innerHTML = '';
                filteredOptions.forEach(option => {
                    const li = document.createElement('li');
                    li.textContent = option;
                    li.addEventListener('click', (event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        input.value = option;
                        suggestions.innerHTML = '';
                        suggestions.style.display = 'none';
                    });
                    suggestions.appendChild(li);
                });

                suggestions.style.display = filteredOptions.length > 0 ? 'block' : 'none';
            };

            input.addEventListener('input', updateSuggestions);
            input.addEventListener('focus', updateSuggestions);
            input.addEventListener('keydown', (event) => {
                if (event.key === 'Enter') event.preventDefault();
            });
        });
    };

    setupAutocomplete('client-university', 'university-suggestions', schools);
    setupAutocomplete('client-department', 'department-suggestions', departments);

    const autocompleteInput = document.getElementById('autocompleteInput');
    const suggestions = document.getElementById('suggestions');

    const updateAffiliateSuggestions = () => {
        const inputValue = autocompleteInput.value.toLowerCase();
        const filteredOptions = options.filter(option => option.toLowerCase().includes(inputValue));

        suggestions.innerHTML = '';
        filteredOptions.forEach(option => {
            const li = document.createElement('li');
            li.textContent = option;
            li.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                autocompleteInput.value = option;
                document.querySelector('input[name="affiliate"]').value = option;
                suggestions.innerHTML = '';
            });
            suggestions.appendChild(li);
        });

        suggestions.style.display = filteredOptions.length > 0 ? 'block' : 'none';
    };

    autocompleteInput.addEventListener('input', updateAffiliateSuggestions);
    autocompleteInput.addEventListener('focus', updateAffiliateSuggestions);
    autocompleteInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') event.preventDefault();
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', (event) => {
        const clickedInput = event.target.closest('.client-university, .client-department, #autocompleteInput');
        const clickedSuggestions = event.target.closest('.university-suggestions, .department-suggestions, .suggestions');

        if (!clickedInput && !clickedSuggestions) {
            document.querySelectorAll('.university-suggestions, .department-suggestions, .suggestions').forEach(suggestions => {
                if (suggestions.style.display !== 'none') suggestions.style.display = 'none';
            });
        }
    });

    // Form validation
    Object.entries(forms).forEach(([formType, form]) => {
        if (form) {
            form.addEventListener('submit', (event) => {
                event.preventDefault();

                let isValid = true;
                let firstInvalidFieldId = null;

                requiredFields[formType].forEach(fieldId => {
                    const field = document.getElementById(fieldId);
                    if (field && !field.value.trim()) {
                        isValid = false;
                        field.classList.add('is-invalid');
                        if (!firstInvalidFieldId) firstInvalidFieldId = fieldId;
                    } else if (field) {
                        field.classList.remove('is-invalid');
                    }
                });

                const universityField = document.getElementById(`${formType}_client_university`);
                if (universityField && !schools.includes(universityField.value)) {
                    isValid = false;
                    universityField.classList.add('is-invalid');
                    if (!firstInvalidFieldId) firstInvalidFieldId = universityField.id;
                } else if (universityField) {
                    universityField.classList.remove('is-invalid');
                }

                if (formType === 'affiliate' && !options.includes(autocompleteInput.value)) {
                    isValid = false;
                    autocompleteInput.classList.add('is-invalid');
                    if (!firstInvalidFieldId) firstInvalidFieldId = 'autocompleteInput';
                } else {
                    autocompleteInput.classList.remove('is-invalid');
                }

                if (!isValid) {
                    const fieldToFocus = document.getElementById(firstInvalidFieldId);
                    if (fieldToFocus) fieldToFocus.focus();
                    alert('Please fill in all required fields' + (formType === 'affiliate' ? ' and select an affiliate from the suggestions.' : '.'));
                } else {
                    form.submit();
                }
            });
        }
    });
});
