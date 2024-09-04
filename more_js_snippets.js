// Append the details text to the corresponding Details div
salesAmountDetailsDiv.innerHTML = salesAmountDetails;
salesCountDetailsDiv.innerHTML = salesCountDetails;
earningsChartDetailsDiv.innerHTML = earningsChartDetails;
// Generate and append the details text for each chart
function createDetailsParagraph(label, labels, data, detailsDiv) {
    let sortedLabels, sortedData;

    // Sort university and department data in descending order
    if (detailsDiv === universityDetailsDiv || detailsDiv === departmentDetailsDiv) {
        const labelDataPairs = labels.map((labelText, index) => ({
            label: labelText,
            data: data[index]
        }));
    
        labelDataPairs.sort((a, b) => b.data - a.data);
    
        sortedLabels = labelDataPairs.map(pair => pair.label);
        sortedData = labelDataPairs.map(pair => pair.data);
    } else {
        sortedLabels = labels;
        sortedData = data;
    }
    labels.forEach((labelText, index) => {
        var paragraph = document.createElement('p');
        paragraph.innerHTML = `<strong>${detailsDiv === hearAboutUsDetailsDiv ? 'Source' : detailsDiv === genderDetailsDiv ? 'Gender' : detailsDiv === studentTypeDetailsDiv ? 'Affiliate Type' : detailsDiv === newAffiliatesDetailsDiv ? 'Week' : detailsDiv === universityDetailsDiv ? 'University': 'Department'}: </strong>${labelText}<br>
                                <strong>Amount:</strong> ${data[index]}`;
        detailsDiv.appendChild(paragraph);
    });
}

createDetailsParagraph('Hear About Us', hearAboutUsLabels, hearAboutUsData, hearAboutUsDetailsDiv);
createDetailsParagraph('Gender Distribution', genderLabels, genderData, genderDetailsDiv);
createDetailsParagraph('Student Type', studentTypeLabels, studentTypeData, studentTypeDetailsDiv);
createDetailsParagraph('New Affiliates per Week', newAffiliatesLabels, newAffiliatesData, newAffiliatesDetailsDiv);
createDetailsParagraph('University Distribution', universityLabels, universityData, universityDetailsDiv);
createDetailsParagraph('Department Distribution', departmentLabels, departmentData, departmentDetailsDiv);


// Function to display conversion rate details
function displayConversionRateDetails(data, labels, containerId) {
    // Get the reference to the container div
    var containerDiv = document.getElementById(containerId);

    // Create a single string for conversion rate details
    let Details = '';

     // Sort data and labels arrays by descending order of conversion rate
     const sortedIndexes = data.map((_, index) => index).sort((a, b) => data[b] - data[a]);
     const sortedData = sortedIndexes.map(index => data[index]);
     const sortedLabels = sortedIndexes.map(index => labels[index]);
     // Generate and append the conversion rate details text
     sortedLabels.forEach((label, index) => {
         Details += `<p><strong>${label}</strong><br>
                                   Conversion Rate: ${sortedData[index]}%</p>`;                                     
     });

    // Update the container div with conversion rate details
    containerDiv.innerHTML = Details;
}

// University Polar Chart Data
var Universitydata = Object.values(UNIVERSITY_CONVERSIONRATES_JSON).map(entry => entry.conversion_rate);
var UniversityConversionRateLabels = Object.values(UNIVERSITY_CONVERSIONRATES_JSON).map(entry => entry.value);
var Departmentdata = Object.values(DEPARTMENT_CONVERSIONRATES_JSON).map(entry => entry.conversion_rate);
var DepartmentConversionRateLabels = Object.values(DEPARTMENT_CONVERSIONRATES_JSON).map(entry => entry.value);

displayConversionRateDetails(HBUdata, hearAboutUsLabels, 'hearAboutUsPolarChartDetails');
displayConversionRateDetails(Genderdata, genderLabels, 'GenderPolarChartDetails');
displayConversionRateDetails(AFFTYdata, studentTypeLabels, 'UndergraduatePolarChartDetails');
displayConversionRateDetails(Universitydata, UniversityConversionRateLabels, 'universityChartPolarDetails');
displayConversionRateDetails(Departmentdata, DepartmentConversionRateLabels, 'DepartmentChartPolarDetails');

function generateLineChartData(labels, data, containerId) {
    // Get the reference to the container div
    var containerDiv = document.getElementById(containerId);
  
    // Create an object to store the data by month
    const dataByMonth = {};
  
    // Populate the data by month
    labels.forEach((label, index) => {
      const month = label;
      if (!dataByMonth[month]) {
        dataByMonth[month] = [];
      }
  
    // Sort the data by highest value first
    const sortedData = data.slice().sort((a, b) => b.data[index] - a.data[index]);
    sortedData.forEach(dataset => {
        const dataPoint = dataset.data[index];
        dataByMonth[month].push({
            label: dataset.label,
            data: dataPoint

        });
      });
    });
  
    // Create a single string for conversion rate details
    let Details = '';
  
    // Display the data in the desired format
    for (const month in dataByMonth) {
      Details += `<p><strong>${month}</strong><br>`;
      dataByMonth[month].forEach(dataPoint => {
        Details += `${dataPoint.label}: ${dataPoint.data}<br>`;
      });
      Details += '</p>';
    }
  
    // Update the container div with conversion rate details
    containerDiv.innerHTML = Details;
  }

generateLineChartData(HEAR_ABOUT_US_LINE_LABELS_JSON, HEAR_ABOUT_US_LINE_DATASETS_JSON, 'hearAboutUsLineChartDetails');
generateLineChartData(GENDER_LABELS_JSON, GENDER_DATASETS_JSON, 'GenderLineChartDetails');
generateLineChartData(UNDERGRADUATE_LABELS_JSON, UNDERGRADUATE_DATASETS_JSON, 'UndergraduateLineChartDetails');
generateLineChartData(UNIVERSITY_LINE_LABELS_JSON, UNIVERSITY_DATASETS_JSON, 'universityChartLineDetails');
generateLineChartData(DEPARTMENT_LINE_LABELS_JSON, DEPARTMENT_DATASETS_JSON, 'DepartmentChartLineDetails');


// Client chart data
const clientUniversityData = CLIENT_UNIVERSITY_DATA;
const clientDepartmentData = CLIENT_DEPARTMENT_DATA;

// Create the client university and department chart
createScrollableClientChart('clientUniChart', clientUniversityData, 'Sales by University');
createScrollableClientChart('clientDeptChart', clientDepartmentData, 'Sales by Department');

// Function to create a scrollable client  chart
function createScrollableClientChart(canvasId, chartData, labelText) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    const chartContainer = ctx.canvas.parentNode;
    
    // Set canvas dimensions
    ctx.canvas.height = Math.max(chartData.length * 25, 400); // Adjust the multiplier when needed
    ctx.canvas.width = chartContainer.offsetWidth;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartData.map(item => item.name),
            datasets: [{
                label: labelText,
                data: chartData.map(item => item.total_sales),
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y', // This makes it a horizontal bar chart
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    position: 'top',
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Sales Made',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        font: {
                            autoSkip: false,
                            size: 14,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        display: true,
                        color: 'rgba(200, 200, 200, 0.5)'
                    },
                    title: {
                        display: true,
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            }
        }
    });
}


// Client university and department data

// Extract names and amounts
const universityNames = clientUniversityData.map(item => item.name);
const universityAmounts = clientUniversityData.map(item => item.total_sales);

const departmentNames = clientDepartmentData.map(item => item.name);
const departmentAmounts = clientDepartmentData.map(item => item.total_sales);

// Get the div to append the details
universityDetailsDiv = document.getElementById('clientUniDetails');
departmentDetailsDiv = document.getElementById('clientDeptDetails');

// Call the createDetailsParagraph function
createDetailsParagraph('Universities', universityNames, universityAmounts, universityDetailsDiv);
createDetailsParagraph('Departments', departmentNames, departmentAmounts, departmentDetailsDiv);
