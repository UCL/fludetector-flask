/*
Fludetector: website, REST API, and data processors for the Fludetector service from UCL.
(c) 2019, UCL <https://www.ucl.ac.uk/

This file is part of Fludetector

Fludetector is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Fludetector is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Fludetector.  If not, see <http://www.gnu.org/licenses/>.
*/
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
            },
            vAxis: {
                minValue: 0
            }
        }

        var chart = new google.visualization.LineChart(document.getElementById('graph'));
        chart.draw(data, options);
    }

    google.charts.load('45', {'packages': ['corechart']});
    google.charts.setOnLoadCallback(drawGraph);
});
