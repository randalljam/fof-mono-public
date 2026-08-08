on titleMatchesCandidate(windowTitle, candidateText)
    ignoring case
        if windowTitle is candidateText then return true
        -- On the target Mac, Cursor reports "editor — workspace" and
        -- "Git Graph — workspace". Only accept the workspace at the end;
        -- a prefix can be a same-named file open in another worktree.
        repeat with separatorText in {" — ", " – ", " - "}
            set separatorValue to separatorText as text
            if windowTitle ends with (separatorValue & candidateText) then return true
            if windowTitle ends with (separatorValue & candidateText & " (Workspace)") then return true
        end repeat
    end ignoring
    return false
end titleMatchesCandidate

on workspaceTitleMatchesCandidate(windowTitle, candidateText)
    ignoring case
        if windowTitle is (candidateText & " (Workspace)") then return true
        repeat with separatorText in {" — ", " – ", " - "}
            if windowTitle ends with ((separatorText as text) & candidateText & " (Workspace)") then return true
        end repeat
    end ignoring
    return false
end workspaceTitleMatchesCandidate

on isPermissionError(errorNumber)
    return errorNumber is -1719 or errorNumber is -1743 or errorNumber is -25211
end isPermissionError

on documentMatchesPath(documentText, targetPath, targetURI)
    if documentText is "" then return false
    if documentText is targetPath or documentText is targetURI then return true
    if documentText starts with (targetPath & "/") then return true
    if documentText starts with (targetURI & "/") then return true
    return false
end documentMatchesPath

on documentMatchesAnyRoot(documentText, documentRootPaths, documentRootURIs)
    repeat with rootIndex from 1 to count documentRootPaths
        if my documentMatchesPath(documentText, item rootIndex of documentRootPaths as text, item rootIndex of documentRootURIs as text) then return true
    end repeat
    return false
end documentMatchesAnyRoot

on matchKindForWindow(cursorWindow, targetPath, documentRootPaths, documentRootURIs, candidateNames)
    tell application "System Events"
        try
            if (value of attribute "AXSubrole" of cursorWindow as text) is not "AXStandardWindow" then return ""
        on error
            return ""
        end try

        try
            set windowTitle to name of cursorWindow as text
            if windowTitle is "" or windowTitle is "Window" then return ""
            set titleMatched to false
            set workspaceTitleMatched to false
            repeat with candidateName in candidateNames
                set candidateText to candidateName as text
                if my titleMatchesCandidate(windowTitle, candidateText) then set titleMatched to true
                if my workspaceTitleMatchesCandidate(windowTitle, candidateText) then set workspaceTitleMatched to true
            end repeat
        on error
            return ""
        end try

        set hasUsableDocument to false
        set documentInAuthorizedRoot to false
        try
            set documentValue to value of attribute "AXDocument" of cursorWindow
            if documentValue is not missing value then
                set documentText to documentValue as text
                if documentText is not "" then
                    set hasUsableDocument to true
                    if my documentMatchesPath(documentText, targetPath, item 1 of documentRootURIs as text) then return "path"
                    set documentInAuthorizedRoot to my documentMatchesAnyRoot(documentText, documentRootPaths, documentRootURIs)
                end if
            end if
        end try
        -- A normal basename title cannot overrule a contradictory document
        -- path. A multi-root .code-workspace title is accepted only when its
        -- active document belongs to a folder parsed from that workspace file.
        if hasUsableDocument then
            if workspaceTitleMatched and documentInAuthorizedRoot then return "title"
            return ""
        end if
        if titleMatched then return "title"
    end tell
    return ""
end matchKindForWindow

on run argv
    if (count argv) < 3 then return "AUTOMATION_FAILED"
    set targetPath to item 1 of argv
    try
        set rootCount to (item 2 of argv) as integer
    on error
        return "AUTOMATION_FAILED"
    end try
    if rootCount < 1 then return "AUTOMATION_FAILED"
    set rootEndIndex to 2 + (rootCount * 2)
    if (count argv) < rootEndIndex then return "AUTOMATION_FAILED"
    set documentRootPaths to {}
    set documentRootURIs to {}
    repeat with rootIndex from 1 to rootCount
        set rootPathIndex to 1 + (rootIndex * 2)
        set end of documentRootPaths to item rootPathIndex of argv
        set end of documentRootURIs to item (rootPathIndex + 1) of argv
    end repeat
    set candidateNames to {}
    set candidateStartIndex to rootEndIndex + 1
    if (count argv) >= candidateStartIndex then set candidateNames to items candidateStartIndex thru -1 of argv

    tell application "System Events"
        if not (exists process "Cursor") then return "APP_NOT_RUNNING"
        tell process "Cursor"
            -- Cursor's AX windows can be absent while the app is on another
            -- Space. Activating an already-running Cursor instance and waiting
            -- for the Space transition makes its complete window list visible.
            set frontmost to true
            delay 1.0
            try
                set cursorWindows to every window
            on error errorMessage number errorNumber
                if my isPermissionError(errorNumber) then return "PERMISSION_REQUIRED"
                return "AUTOMATION_FAILED"
            end try
            if (count cursorWindows) is 0 then return "TARGET_NOT_FOUND"

            set matchingWindows to {}
            repeat with cursorWindow in cursorWindows
                set matchedKind to my matchKindForWindow(cursorWindow, targetPath, documentRootPaths, documentRootURIs, candidateNames)
                if matchedKind is not "" then
                    set end of matchingWindows to cursorWindow
                end if
            end repeat

            set matchCount to count matchingWindows
            if matchCount is 0 then return "TARGET_NOT_FOUND"
            if matchCount is greater than 1 then return "AMBIGUOUS" & tab & matchCount
            set targetWindow to item 1 of matchingWindows

            -- Cursor is already frontmost. Focus and raise the selected window,
            -- then wait for any target-Space transition and verify the result.
            try
                set value of attribute "AXMinimized" of targetWindow to false
            end try
            try
                perform action "AXRaise" of targetWindow
                try
                    set value of attribute "AXMain" of targetWindow to true
                end try
                perform action "AXRaise" of targetWindow
            on error
                return "AUTOMATION_FAILED"
            end try

            -- Space transitions invalidate AX references and complete at
            -- variable speeds. Poll a bounded number of times, re-enumerating
            -- and uniquely rematching real standard windows on each attempt.
            set verifiedKind to ""
            repeat with verificationAttempt from 1 to 8
                delay 0.5
                try
                    set verifiedWindows to every window
                    set verifiedMatches to {}
                    set verifiedKinds to {}
                    repeat with verifiedWindow in verifiedWindows
                        set currentKind to my matchKindForWindow(verifiedWindow, targetPath, documentRootPaths, documentRootURIs, candidateNames)
                        if currentKind is not "" then
                            set end of verifiedMatches to verifiedWindow
                            set end of verifiedKinds to currentKind
                        end if
                    end repeat
                    if (count verifiedMatches) is 1 then
                        set focusedWindow to item 1 of verifiedMatches
                        set focusedWindowIsMain to value of attribute "AXMain" of focusedWindow
                        if focusedWindowIsMain is true then
                            try
                                set frontmost to true
                                perform action "AXRaise" of focusedWindow
                                delay 0.1
                            end try
                            if frontmost is true then
                                set verifiedKind to item 1 of verifiedKinds
                                exit repeat
                            end if
                        end if
                    end if
                on error
                    -- A window list may be replaced during a Space transition.
                end try
            end repeat
            if verifiedKind is "" then return "AUTOMATION_FAILED"
            if frontmost is not true then return "AUTOMATION_FAILED"
            return "FOCUSED" & tab & verifiedKind
        end tell
    end tell
end run
