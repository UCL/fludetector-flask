$(function () {
    $('.datepicker').datetimepicker({
        format: 'YYYY-MM-DD',
        allowInputToggle: true
    });

    var drawGraph = function() {
        var data = google.visualization.arrayToDataTable(CHART_DATA);

        var options = {
            theme: 'maximised',
            title: 'Influenza-Like Illness Rate per Day',
            curveType: 'function',
            interpolateNulls: true,
            legend: {position: 'right'},
            hAxis: {
                showTextEvery: 1
            }
        }

        var chart = new google.visualization.LineChart(document.getElementById('graph'));
        chart.draw(data, options);
    }

    google.charts.load('current', {'packages': ['corechart']});
    google.charts.setOnLoadCallback(drawGraph);
});
