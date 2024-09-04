
// Show the message for 3 seconds
const Messages = document.querySelectorAll('.alert');
if (Messages.length > 0) {
    setTimeout(() => {
        Messages.forEach(message => {
            message.style.display = 'none';
        });
    }, 5000);
}

document.addEventListener('DOMContentLoaded', function () {
    const checkboxes = document.querySelectorAll('.card-input-element');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function () {
            const card = checkbox.closest('.card-custom');
            const icon = card.querySelector('.card-title i');
            
            if (checkbox.checked) {
                card.classList.add('selected');
                icon.classList.remove('fa-person-circle-plus');
                icon.classList.add('fa-person-circle-check');
            } else {
                card.classList.remove('selected');
                icon.classList.remove('fa-person-circle-check');
                icon.classList.add('fa-person-circle-plus');
            }
        });
    });
});
/////////////////

function takeScreenshot(url, take) {
    const captureElement = document.getElementById(take);
    html2canvas(captureElement).then(function(canvas) {
        var dataURL = canvas.toDataURL("image/png");
        sendToView(dataURL, url);
    });
}

// Post data to a view
function sendToView(dataURL, url) {
    // Create a form dynamically
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = url;

    // Add CSRF token
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = getCsrfToken();
    form.appendChild(csrfInput);

    // Add the data
    const dataInput = document.createElement('input');
    dataInput.type = 'hidden';
    dataInput.name = 'sentData';
    dataInput.value = dataURL;
    form.appendChild(dataInput);

    // Add the form to the document and submit it
    document.body.appendChild(form);
    form.submit();
}

function capture() {
    const shot = document.getElementById('screenshotBtn');
    const url = shot.getAttribute('data-url');
    const take = shot.getAttribute('data-capture');
    takeScreenshot(url, take);
}

// Helper function to get CSRF token
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// Send payment notification to view
function sendEmail() {
    const send = document.getElementById('EmailMe');
    const view = send.getAttribute('data-url');
    const subject = send.getAttribute('data-subject');
    const body = document.querySelector('.notification-container').innerText;
    const message = [subject, body];
    sendToView(message, view);
}


// End promo chart
function createEndPromoChart(totalEarnings, avgEarnings) {
    var ctx = document.getElementById('endPromoChart').getContext('2d');
    var chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Total Affiliate Earnings', 'Average Earnings per Affiliate'],
            datasets: [{
                label: 'Earnings (Naira)',
                data: [totalEarnings, avgEarnings],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.6)',
                    'rgba(153, 102, 255, 0.6)'
                ],
                borderColor: [
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Price (Naira)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Affiliate Earning Summary'
                    }
                }
            }
        }
    });
}

// Create the End promo chart
document.addEventListener('DOMContentLoaded', function() {
    var chartContainer = document.getElementById('endPromoChart');
    if (chartContainer) {
        var totalEarnings = parseFloat(chartContainer.dataset.totalEarnings);
        var avgEarnings = parseFloat(chartContainer.dataset.avgEarnings);
        createEndPromoChart(totalEarnings, avgEarnings);
    }
});
