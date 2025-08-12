document.addEventListener('DOMContentLoaded', function() {
    feather.replace();

    // The data for the chart will be passed from the Flask backend via Jinja templates.
    // We'll grab the data from the script tag in the HTML template.
    const chartDataElement = document.getElementById('chart-data');
    if (chartDataElement) {
        const monthlySalesLabels = JSON.parse(chartDataElement.getAttribute('data-labels'));
        const monthlySalesData = JSON.parse(chartDataElement.getAttribute('data-data'));
        
        const ctx = document.getElementById('monthlySalesChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: monthlySalesLabels,
                datasets: [{
                    label: 'Monthly Sales (₹)',
                    data: monthlySalesData,
                    backgroundColor: 'rgba(255, 87, 34, 0.2)',
                    borderColor: 'rgba(255, 87, 34, 1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(200, 200, 200, 0.2)'
                        },
                        ticks: {
                            callback: function(value, index, ticks) {
                                return '₹' + value;
                            }
                        }
                    }
                }
            }
        });
    }
});