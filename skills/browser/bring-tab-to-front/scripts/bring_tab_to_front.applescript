-- Bring a unique Chrome tab's window to the OS front without surfacing siblings.
-- Usage (normally via bring_tab_to_front.sh):
--   osascript bring_tab_to_front.applescript <urlNeedle> <windowNamePrefix> <python> <helper.py>
-- Defaults when args omitted: urlNeedle=127.0.0.1:8790  windowNamePrefix=holodeck
-- Success: OK\tmatchedURL\tmatchedTitle\tfrontURL\tfrontTitle
-- Abort:   ABORT\treason\t[detail...]
--
-- Does NOT minimize sibling windows. Does NOT use System Events `set frontmost`
-- (that raises every Chrome window above other apps). Instead:
--   1) snapshot sibling geometry / minimized / Chrome index
--   2) Window-menu select the target (makes it Chrome's front window only)
--   3) activate_front_window_only.py (SetFrontProcess FrontWindowOnly)
--   4) restore sibling geometry / minimized / index if anything moved

on run argv
	set urlNeedle to "127.0.0.1:8790"
	set windowNamePrefix to "holodeck"
	set pythonPath to ""
	set helperPath to ""
	if (count of argv) is greater than or equal to 1 then
		if item 1 of argv is not "" then set urlNeedle to item 1 of argv
	end if
	if (count of argv) is greater than or equal to 2 then
		if item 2 of argv is not "" then set windowNamePrefix to item 2 of argv
	end if
	if (count of argv) is greater than or equal to 3 then
		set pythonPath to item 3 of argv
	end if
	if (count of argv) is greater than or equal to 4 then
		set helperPath to item 4 of argv
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

		set active tab index of window (matchWindowIndex as integer) to (matchTabIndex as integer)
		try
			set minimized of window (matchWindowIndex as integer) to false
		end try
		set matchedTitle to title of active tab of window (matchWindowIndex as integer) as text

		-- Snapshot every Chrome window's index / bounds / miniaturized (by active-tab title key).
		set siblingSnapshots to {}
		repeat with windowIndex from 1 to (count of windows)
			set w to window windowIndex
			set wTitle to title of active tab of w as text
			set wMini to false
			try
				set wMini to miniaturized of w
			end try
			set end of siblingSnapshots to {wTitle, windowIndex, wMini}
		end repeat
	end tell

	set targetSEName to ""
	tell application "System Events"
		set chromePID to unix id of process "Google Chrome"
		tell process "Google Chrome"
			-- Snapshot SE geometry for named windows (skip empty AX chrome).
			set seSnapshots to {}
			set targetWindow to missing value
			set raiseCount to 0
			repeat with uiWindow in (get windows)
				try
					set winName to name of uiWindow as text
				on error
					set winName to ""
				end try
				if winName is not "" then
					set winPos to position of uiWindow
					set winSize to size of uiWindow
					set winMini to false
					try
						set winMini to value of attribute "AXMinimized" of uiWindow
					end try
					set end of seSnapshots to {winName, winPos, winSize, winMini}
					set isTarget to false
					if matchedTitle is not "" and winName starts with matchedTitle then
						set isTarget to true
					else if winName starts with windowNamePrefix then
						set isTarget to true
					end if
					if isTarget then
						set raiseCount to raiseCount + 1
						set targetWindow to uiWindow
						set targetSEName to winName
					end if
				end if
			end repeat

			if raiseCount is 0 then
				return "ABORT" & tab & "no System Events window matches title/prefix" & tab & matchedTitle & tab & windowNamePrefix
			end if
			if raiseCount is greater than 1 then
				return "ABORT" & tab & "multiple System Events windows match" & tab & (raiseCount as text) & tab & matchedTitle
			end if

			-- Window menu uses the short tab title (not the full SE name).
			try
				click menu item matchedTitle of menu 1 of menu bar item "Window" of menu bar 1
			on error errMsg
				return "ABORT" & tab & "Window menu click failed" & tab & matchedTitle & tab & errMsg
			end try

			try
				set value of attribute "AXMinimized" of targetWindow to false
			end try
			perform action "AXRaise" of targetWindow
			try
				set value of attribute "AXMain" of targetWindow to true
			end try
		end tell
	end tell

	-- Front-window-only activation (does not surface sibling Chrome windows).
	if pythonPath is "" or helperPath is "" then
		return "ABORT" & tab & "python/helper paths required for front-window-only activate"
	end if
	try
		set activateOut to do shell script (quoted form of pythonPath) & " " & (quoted form of helperPath) & " " & (chromePID as text)
	on error errMsg
		return "ABORT" & tab & "front-window-only activate failed" & tab & errMsg
	end try
	if activateOut is not "OK" then
		return "ABORT" & tab & "front-window-only activate failed" & tab & activateOut
	end if

	-- Restore sibling Chrome windows to prior geometry / minimized / index.
	tell application "Google Chrome"
		repeat with snap in siblingSnapshots
			set snapTitle to item 1 of snap
			set snapIndex to item 2 of snap
			set snapMini to item 3 of snap
			if snapTitle is not matchedTitle then
				repeat with windowIndex from 1 to (count of windows)
					set w to window windowIndex
					if (title of active tab of w as text) is snapTitle then
						try
							set index of w to snapIndex
						end try
						try
							set miniaturized of w to snapMini
						end try
						exit repeat
					end if
				end repeat
			end if
		end repeat
	end tell

	tell application "System Events"
		tell process "Google Chrome"
			repeat with snap in seSnapshots
				set snapName to item 1 of snap
				set snapPos to item 2 of snap
				set snapSize to item 3 of snap
				set snapMini to item 4 of snap
				if snapName is not targetSEName then
					repeat with uiWindow in (get windows)
						try
							set winName to name of uiWindow as text
						on error
							set winName to ""
						end try
						if winName is snapName then
							try
								set value of attribute "AXMinimized" of uiWindow to snapMini
							end try
							try
								set position of uiWindow to snapPos
								set size of uiWindow to snapSize
							end try
							exit repeat
						end if
					end repeat
				end if
			end repeat
			-- Keep the target raised/main after sibling restore.
			try
				set targetWindow to first window whose name is targetSEName
				perform action "AXRaise" of targetWindow
				set value of attribute "AXMain" of targetWindow to true
			end try
		end tell
	end tell

	set frontURL to ""
	set frontTitle to ""
	set deadline to (current date) + 3
	repeat
		tell application "Google Chrome"
			try
				set frontURL to URL of active tab of front window as text
				set frontTitle to title of active tab of front window as text
			on error errMsg
				set frontURL to ""
				set frontTitle to ""
			end try
		end tell
		if frontURL contains urlNeedle then exit repeat
		if (current date) is greater than or equal to deadline then
			return "ABORT" & tab & "front tab never matched after raise" & tab & frontURL & tab & frontTitle
		end if
		delay 0.1
	end repeat

	return "OK" & tab & matchedURL & tab & matchedTitle & tab & frontURL & tab & frontTitle
end run
