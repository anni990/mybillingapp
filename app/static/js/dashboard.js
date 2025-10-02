document.addEventListener('DOMContentLoaded', function() {
    feather.replace();

    // The data for the chart will be passed from the Flask backend via Jinja templates.
    // We'll grab the data from the script tag in the HTML template.
    const chartDataElement = document.getElementById('chart-data');
    const ctx = document.getElementById('monthlySalesChart');
    
    console.log('Chart canvas element:', ctx);
    console.log('Chart data element:', chartDataElement);
    
    if (chartDataElement && ctx) {
        try {
            const labelsAttr = chartDataElement.getAttribute('data-labels');
            const dataAttr = chartDataElement.getAttribute('data-data');
            
            console.log('Raw labels:', labelsAttr);
            console.log('Raw data:', dataAttr);
            
            const monthlySalesLabels = JSON.parse(labelsAttr || '[]');
            const monthlySalesData = JSON.parse(dataAttr || '[]');
            
            console.log('Parsed labels:', monthlySalesLabels);
            console.log('Parsed data:', monthlySalesData);
            
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: monthlySalesLabels,
                    datasets: [{
                        label: 'Monthly Sales (₹)',
                        data: monthlySalesData,
                        backgroundColor: 'rgba(237, 106, 62, 0.2)',
                        borderColor: '#ed6a3e',
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
            console.log('Chart created successfully');
        } catch (error) {
            console.error('Error creating chart:', error);
        }
    } else {
        console.log('Chart elements not found - canvas:', !!ctx, 'data element:', !!chartDataElement);
    }
});
