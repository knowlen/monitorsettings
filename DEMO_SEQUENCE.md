# Demo Recording Sequence

Follow this sequence when recording the asciinema demo:

## Setup
1. Make sure you have at least one external monitor connected with DDC/CI enabled
2. Set terminal to a reasonable size (e.g., 80x24 or 100x30)
3. Clear the terminal before starting

## Recording Steps

1. **Start Recording**
   ```bash
   ./record_demo.sh
   ```

2. **Launch the Application**
   ```bash
   monitorsettings
   ```
   - Wait for initialization to complete
   - Let viewers see the initial state (2-3 seconds)

3. **Demonstrate Brightness Control**
   - Press `→` 3-4 times (increase brightness)
   - Wait 1 second between presses to show the animation
   - Press `←` 3-4 times (decrease brightness)
   - Show the pending indicator (asterisk) appearing

4. **Demonstrate Step Size Adjustment**
   - Press `↑` 2-3 times to increase step size
   - Press `→` once to show larger brightness jump
   - Press `↓` to decrease step size back

5. **Demonstrate Display Selection**
   - Press `1` to select Display 1 only
   - Press `→` to adjust only Display 1
   - Press `2` to select Display 2
   - Press `→` to adjust only Display 2
   - Press `0` to select all displays again

6. **Exit the Application**
   - Press `q` to quit
   - Let the exit message display

7. **End Recording**
   - Press `Ctrl+D` to stop asciinema recording

## After Recording

1. Preview your recording:
   ```bash
   asciinema play demo.cast
   ```

2. If happy with it, upload:
   ```bash
   asciinema upload demo.cast
   ```

3. Copy the provided URL and embed code

4. Update README.md with the embed code (replacing the screenshot)

## Tips
- Keep total recording under 60 seconds
- Move deliberately, not too fast
- Pause briefly after each action
- If you make a mistake, just exit and re-record