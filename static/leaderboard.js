document.addEventListener('DOMContentLoaded', function() {
    const reloadButton = document.getElementById('reload-btn');
    const leaderboardTableBody = document.querySelector('#leaderboard-table tbody');

    // Fetch data from the API
    function fetchLeaderboardData() {
        fetch('http://127.0.0.1:5000/players')
            .then(response => response.json())
            .then(data => {
                // Clear the table before populating with new data
                leaderboardTableBody.innerHTML = '';

                // Loop through each player and add a row to the table
                data.forEach(player => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${player.name}</td>
                        <td>${player.birdies}</td>
                        <td>${player.date}</td>
                    `;
                    leaderboardTableBody.appendChild(row);
                });
            })
            .catch(error => {
                console.error('Error fetching leaderboard data:', error);
            });
    }

    // Initial fetch
    fetchLeaderboardData();

    // Reload leaderboard when button is clicked
    reloadButton.addEventListener('click', fetchLeaderboardData);
});
 
