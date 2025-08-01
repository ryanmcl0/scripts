document.getElementById('switch-to-baidu').addEventListener('click', () => {
  chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
    chrome.scripting.executeScript({
      target: {tabId: tabs[0].id},
      function: switchToBaidu
    });
  });
});

document.getElementById('switch-to-google').addEventListener('click', () => {
  chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
    chrome.scripting.executeScript({
      target: {tabId: tabs[0].id},
      function: switchToGoogle
    });
  });
});

function switchToBaidu() {
  let url = window.location.href;
  let match = url.match(/@([0-9.]+),([0-9.]+),/);
  if (match) {
    let lat = match[1];
    let lon = match[2];
    let baiduUrl = `https://map.baidu.com/?latlng=${lat},${lon}&output=html`;
    window.open(baiduUrl, '_blank');
  } else {
    alert("Coordinates not found!");
  }
}

function switchToGoogle() {
  let url = window.location.href;
  let match = url.match(/lat=([0-9.]+)&lng=([0-9.]+)/);
  if (match) {
    let lat = match[1];
    let lon = match[2];
    let googleUrl = `https://www.google.com/maps/@${lat},${lon},15z`;
    window.open(googleUrl, '_blank');
  } else {
    alert("Coordinates not found!");
  }
}