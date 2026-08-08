-- Soft-reload a unique Chrome tab by URL substring (no focus / no keystrokes).
-- Usage:
--   osascript skills/browser/hard-reload-tab/scripts/soft_reload_tab.applescript [urlNeedle]
-- Default urlNeedle: 127.0.0.1:8790
-- Success: OK\tmatchedURL\tmatchedTitle
-- Abort:   ABORT\treason\t[detail...]

on run argv
	set urlNeedle to "127.0.0.1:8790"
	if (count of argv) is greater than or equal to 1 then
		if item 1 of argv is not "" then set urlNeedle to item 1 of argv
	end if

	if running of application "Google Chrome" is false then
		return "ABORT" & tab & "Chrome not running"
	end if

	tell application "Google Chrome"
		set matchWindowIndex to 0
		set matchTabIndex to 0
		set matchCount to 0
		set matchedURL to ""
		set matchedTitle to ""

		repeat with windowIndex from 1 to (count of windows)
			set browserWindow to item windowIndex of windows
			repeat with tabIndex from 1 to (count of tabs of browserWindow)
				set browserTab to item tabIndex of tabs of browserWindow
				set tabURL to URL of browserTab as text
				if tabURL contains urlNeedle then
					set matchCount to matchCount + 1
					set matchWindowIndex to windowIndex
					set matchTabIndex to tabIndex
					set matchedURL to tabURL
					set matchedTitle to title of browserTab as text
				end if
			end repeat
		end repeat

		if matchCount is 0 then
			return "ABORT" & tab & "no tab URL contains" & tab & urlNeedle
		end if
		if matchCount is greater than 1 then
			return "ABORT" & tab & "multiple tabs match" & tab & (matchCount as text) & tab & urlNeedle
		end if

		reload item (matchTabIndex as integer) of tabs of window (matchWindowIndex as integer)
	end tell

	return "OK" & tab & matchedURL & tab & matchedTitle
end run
