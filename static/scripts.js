async function fetchPlaylists() {
  const listElement = document.getElementById("playlists-list");
  const refreshButton = document.getElementById("refresh-playlists");
  refreshButton.disabled = true;
  listElement.innerHTML = "<li>Loading playlists...</li>";

  try {
    const response = await fetch("/playlists");
    if (!response.ok) throw new Error("Network response was not ok");
    const playlists = await response.json();

    if (playlists.length === 0) {
      listElement.innerHTML = "<li>No playlists found.</li>";
      return;
    }

    listElement.innerHTML = ""; // Clear loading text

    playlists.forEach(playlist => {
      const li = document.createElement("li");
      li.className = "playlist-item";

      const contentWrapper = document.createElement("div");
      contentWrapper.className = "playlist-content";

      const a = document.createElement("a");
      a.href = playlist.url;
      a.textContent = playlist.name || playlist.url;
      a.target = "_blank";
      a.className = "playlist-link";
      contentWrapper.appendChild(a);

      const statusSpan = document.createElement("span");
      statusSpan.className = "playlist-status";

      if (playlist.import_status === "importing") {
        const spinner = document.createElement("div");
        spinner.className = "spinner";
        statusSpan.appendChild(spinner);
      } else if (playlist.import_status === "imported") {
        statusSpan.textContent = "Imported";
      }

      contentWrapper.appendChild(statusSpan);
      li.appendChild(contentWrapper);
      listElement.appendChild(li);
    });
  } catch (error) {
    listElement.innerHTML = `<li>Error loading playlists: ${error.message}</li>`;
  } finally {
    refreshButton.disabled = false;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  fetchPlaylists();
  setInterval(fetchPlaylists, 5000);  // refresh every 5 seconds
});