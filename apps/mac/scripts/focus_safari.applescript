on run argv
    if (count argv) is not 2 then return "AUTOMATION_FAILED"
    set targetURL to item 1 of argv
    set targetTitle to item 2 of argv
    if targetURL is "" and targetTitle is "" then return "AUTOMATION_FAILED"
    if running of application "Safari" is false then return "APP_NOT_RUNNING"

    tell application "Safari"
        set matches to {}
        repeat with windowIndex from 1 to count windows
            set browserWindow to item windowIndex of windows
            repeat with tabIndex from 1 to count tabs of browserWindow
                set browserTab to item tabIndex of tabs of browserWindow
                set urlMatches to targetURL is ""
                set titleMatches to targetTitle is ""
                if targetURL is not "" then set urlMatches to (URL of browserTab as text) is targetURL
                if targetTitle is not "" then set titleMatches to (name of browserTab as text) is targetTitle
                if urlMatches and titleMatches then set end of matches to {windowIndex, tabIndex}
            end repeat
        end repeat

        set matchCount to count matches
        if matchCount is 0 then return "TARGET_NOT_FOUND"
        if matchCount is greater than 1 then return "AMBIGUOUS" & tab & matchCount
        set targetMatch to item 1 of matches
        set targetWindowIndex to item 1 of targetMatch
        set targetTabIndex to item 2 of targetMatch
        set current tab of window (targetWindowIndex as integer) to tab (targetTabIndex as integer) of window (targetWindowIndex as integer)
        try
            set miniaturized of window (targetWindowIndex as integer) to false
        end try
        set index of window (targetWindowIndex as integer) to 1
        activate
        if targetURL is not "" and targetTitle is not "" then return "FOCUSED" & tab & "url_title"
        if targetURL is not "" then return "FOCUSED" & tab & "url"
        return "FOCUSED" & tab & "title"
    end tell
end run
