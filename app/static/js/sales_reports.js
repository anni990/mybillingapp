// sales_reports.js

document.addEventListener('DOMContentLoaded', function () {
    // Chart.js line chart
    const ctx = document.getElementById('salesChart').getContext('2d');
    const chartLabels = window.CHART_LABELS;
    const chartValues = window.CHART_VALUES;
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartLabels,
            datasets: [{
                label: 'Total Sales (₹)',
                data: chartValues,
                borderColor: '#ed6a3e',
                backgroundColor: 'rgba(237,106,62,0.1)',
                tension: 0.3,
                fill: true,
                pointRadius: 5,
                pointBackgroundColor: '#ed6a3e',
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: true }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
});

function downloadTableAsCSV() {
    let csv = '';
    document.querySelectorAll('table thead tr').forEach(row => {
        csv += Array.from(row.children).map(cell => '"' + cell.innerText + '"').join(',') + '\n';
    });
    document.querySelectorAll('table tbody tr').forEach(row => {
        csv += Array.from(row.children).map(cell => '"' + cell.innerText + '"').join(',') + '\n';
    });
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sales_report.csv';
    a.click();
    window.URL.revokeObjectURL(url);
} 