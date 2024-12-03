function submitSearch() {
    const query = document.getElementById('searchInput').value;

    fetch('/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: query })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('result').innerText = data.result;
    })
    .catch(error => console.error('Error:', error));
}