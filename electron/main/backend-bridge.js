const { app } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

// Helper function to run python commands via the bundled backend
function runPythonCommand(command, kwargs, event) {
    const buildDir = path.resolve(__dirname, '..', '..', 'build');
    let backendPath;
    if (app.isPackaged) {
        backendPath = path.join(process.resourcesPath, 'fourdst-backend');
    } else {
        backendPath = path.join(buildDir, 'electron', 'dist', 'fourdst-backend', 'fourdst-backend');
    }

    console.log(`[MAIN_PROCESS] Spawning backend: ${backendPath}`);
    const args = [command, JSON.stringify(kwargs)];
    console.log(`[MAIN_PROCESS] With args: [${args.join(', ')}]`);

    return new Promise((resolve) => {
        const process = spawn(backendPath, args);
        let stdoutBuffer = '';
        let errorOutput = '';

        process.stderr.on('data', (data) => {
            errorOutput += data.toString();
            console.error('Backend STDERR:', data.toString().trim());
        });

        const isStreaming = command === 'fill_bundle';

        process.stdout.on('data', (data) => {
            const chunk = data.toString();
            stdoutBuffer += chunk;

            if (isStreaming && event) {
                // Process buffer line by line for streaming commands
                let newlineIndex;
                while ((newlineIndex = stdoutBuffer.indexOf('\n')) >= 0) {
                    const line = stdoutBuffer.substring(0, newlineIndex).trim();
                    stdoutBuffer = stdoutBuffer.substring(newlineIndex + 1);

                    if (line) {
                        try {
                            const parsed = JSON.parse(line);
                            if (parsed.type === 'progress') {
                                event.sender.send('fill-bundle-progress', parsed.data);
                            } else {
                                // Not a progress update, put it back in the buffer for final processing
                                stdoutBuffer = line + '\n' + stdoutBuffer;
                                break; // Stop processing lines
                            }
                        } catch (e) {
                            // Ignore parsing errors for intermediate lines in a stream
                        }
                    }
                }
            }
        });

        process.on('close', (code) => {
            console.log(`[MAIN_PROCESS] Backend process exited with code ${code}`);
            let resultData = null;

            try {
                // Core functions now return clean JSON directly
                const finalJson = JSON.parse(stdoutBuffer.trim());
                resultData = finalJson;  // Use the JSON response directly
            } catch (e) {
                console.error(`[MAIN_PROCESS] Could not parse backend output as JSON: ${e}`);
                console.error(`[MAIN_PROCESS] Raw output: "${stdoutBuffer}"`);
                // If parsing fails, return a structured error response
                resultData = { 
                    success: false, 
                    error: `JSON parsing failed: ${e.message}`,
                    raw_output: stdoutBuffer 
                };
            }

            const finalError = errorOutput.trim();
            if (finalError && !resultData) {
                resolve({ success: false, error: finalError });
            } else if (resultData) {
                resolve(resultData);
            } else {
                const errorMessage = finalError || `The script finished without returning a result (exit code: ${code})`;
                resolve({ success: false, error: errorMessage });
            }
        });

        process.on('error', (err) => {
            resolve({ success: false, error: `Failed to start backend process: ${err.message}` });
        });
    });
}

module.exports = {
    runPythonCommand
};
