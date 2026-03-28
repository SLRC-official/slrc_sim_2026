<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wi-Fi Connection Guide (nmcli)</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 40px;
            background-color: #1e1e1e;  /* dark background */
            color: #ffffff;             /* light text */
        }
        pre {
            background: #222;
            color: #eee;
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
        }
        code {
            font-family: monospace;
        }
        .container {
            background: #1e1e1e;
            color: #ffffff;
        }
        .note {
            background: #eef6ff;
            padding: 12px;
            border-left: 4px solid #007bff;
            margin-top: 15px;
            border-radius: 6px;
        }
        .gif-container {
            text-align: center;
            margin-top: 20px;
        }
        img {
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 0 8px rgba(0,0,0,0.1);
        }
        footer {
            margin-top: 30px;
            font-size: 0.9em;
            color: #666;
            text-align: center;
        }
    </style>
</head>
<body>

<div class="container">
    <h1>📶 Connecting to a Wi-Fi Network Using <code>nmcli</code></h1>
    <p>Follow the steps below to connect to a Wi-Fi network from the terminal.</p>
    <h2>1. Check Available Networks</h2>
    <p>Scan and verify that your desired network is available:</p>
    <pre><code>nmcli device wifi list</code></pre>
    <h2>2. Connect to the Network</h2>
    <p>Once you confirm the network is listed, connect using:</p>
    <pre><code>sudo nmcli device wifi connect "SLRC_5G" password "SLRC@2026"</code></pre>
    <h2>🎥 Demo</h2>
    <p>Refer to the GIF below for a step-by-step visual guide:</p>
    <div class="gif-container">
        <!-- Replace the file name below with your actual GIF -->
        <img src="wifi_change.gif" alt="WiFi connection demo">
    </div>
    <footer>
    </footer>
</div>

</body>
</html>