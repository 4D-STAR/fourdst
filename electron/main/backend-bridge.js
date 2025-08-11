const { app } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

// Helper function to run python commands via the bundled backend
function runPythonCommand(command, kwargs, event) {
    const buildDir = path.resolve(__dirname, '..', '..', 'build');
    let backendPath;
    
    // Determine executable name based on platform
    const executableName = process.platform === 'win32' ? 'fourdst-backend.exe' : 'fourdst-backend';
    
    if (app.isPackaged) {
        // In packaged app, backend is in resources/backend/ directory
        backendPath = path.join(process.resourcesPath, 'backend', executableName);
    } else {
        // In development, use the meson build output
        backendPath = path.join(buildDir, 'electron', 'dist', 'fourdst-backend', executableName);
    }

    console.log(`[MAIN_PROCESS] Spawning backend: ${backendPath}`);
    const args = [command, JSON.stringify(kwargs)];
    console.log(`[MAIN_PROCESS] With args: [${args.join(', ')}]`);

    return new Promise((resolve) => {
        const process = spawn(backendPath, args);
        let stdoutBuffer = '';
        let errorOutput = '';

        process.stderr.on('data', (data) => {
            const stderrChunk = data.toString();
            errorOutput += stderrChunk;
            console.error('Backend STDERR:', stderrChunk.trim());
            
            // For fill_bundle, forward stderr to frontend for terminal display
            if (isStreaming && event && command === 'fill_bundle') {
                // Parse stderr lines and send them as progress updates
                const lines = stderrChunk.split('\n').filter(line => line.trim());
                lines.forEach(line => {
                    const trimmedLine = line.trim();
                    
                    // Check if this is a structured progress message
                    if (trimmedLine.startsWith('[PROGRESS] {')) {
                        try {
                            // Extract JSON from [PROGRESS] prefix
                            const jsonStr = trimmedLine.substring('[PROGRESS] '.length);
                            const progressData = JSON.parse(jsonStr);
                            console.log(`[MAIN_PROCESS] Parsed progress data:`, progressData);
                            
                            // Send as proper progress update
                            event.sender.send('fill-bundle-progress', progressData);
                        } catch (e) {
                            console.error(`[MAIN_PROCESS] Failed to parse progress JSON: ${trimmedLine}`, e);
                            // Fallback to stderr if JSON parsing fails
                            event.sender.send('fill-bundle-progress', {
                                type: 'stderr',
                                stderr: trimmedLine
                            });
                        }
                    } else {
                        // Only skip very specific system messages, include everything else as stderr
                        const shouldSkip = trimmedLine.includes('[BRIDGE_INFO]') || 
                                         trimmedLine.includes('--- Python backend bridge') ||
                                         trimmedLine.startsWith('[PROGRESS]') || // Skip non-JSON progress messages
                                         trimmedLine === '';
                        
                        if (!shouldSkip) {
                            console.log(`[MAIN_PROCESS] Forwarding stderr to frontend: ${trimmedLine}`);
                            event.sender.send('fill-bundle-progress', {
                                type: 'stderr',
                                stderr: trimmedLine
                            });
                        }
                    }
                });
            }
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
            console.log(`[MAIN_PROCESS] Backend path used: ${backendPath}`);
            console.log(`[MAIN_PROCESS] App packaged: ${app.isPackaged}`);
            console.log(`[MAIN_PROCESS] Resources path: ${process.resourcesPath || 'N/A'}`);
            console.log(`[MAIN_PROCESS] Raw stdout buffer length: ${stdoutBuffer.length}`);
            console.log(`[MAIN_PROCESS] Raw stdout first 200 chars: "${stdoutBuffer.substring(0, 200)}"`);
            console.log(`[MAIN_PROCESS] Error output: "${errorOutput}"`);
            
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
                    raw_output: stdoutBuffer,
                    backend_path: backendPath,
                    is_packaged: app.isPackaged,
                    exit_code: code,
                    stderr_output: errorOutput
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
