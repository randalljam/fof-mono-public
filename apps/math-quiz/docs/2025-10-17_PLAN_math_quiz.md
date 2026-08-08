## 10-17-2025
[] Add the ability and analysis to flag to remove a point. And enter flag from a pull down of the reason.

## 1-30-2025
[ ] local dev page
[ ] phone version with problem on top half and number pad below
[ ] auto enter answer - think already done
[ ] custom problem sequences
[ ] audio clips for each single digit addition problem

 
## Tasks
[] Add a pause button - how to implement? restart question?
[] Create number groups according to gsheet
[] Add adaptive questions
   [] import previous jsons and jsons_to_pass function
[] display map in real time
   [] toggle between heatmap and pass criteria (2 below threshold)


### 10-21-2024 morning fixes
[x] Remove welcome message from top, keep only at beginning
[x] Adjust first page layout to prevent fill-in interference
[x] Add Download buttons to initial screen and console log print of jsons
[x] Add check For download to see if there are no JSON files and if not pop up an error that says no JSON files, nothing to download.
[x] Investigate and fix double enter key bug
[x] Fix minus pronunciation for subtraction
[x] Correct times and divide operations pronunciations
[x] Tweak custom page to have title and everything fit on screen
[] Extend time listening to 20 seconds and then end question 
[] Add pause button
[] Fix intermittent bug where it does multiple questions in a row (try entering answers fast by typing)

### Layout and styling
[] Move check boxes to the left of the read problems and enable speech.

[] .cursorrules edit for css changes and docstrings

[] Fix correction to put answer into box
[] Consider Retry button, but likely would want to add that in json
[] Implement problem exclusion feature for distracted attempts
    [] Design interaction for marking/excluding problems
[] Set up question list for consistent problem sets
    [] Implement progression tracking

[] Add speech detection mode
    [] Implement keyword recognition
    [] Add parent input option for problem exclusion
[] Create graph for specific problem times across multiple attempts
    [] Implement scroll-over functionality


- Remove the welcome message for the arithmetic fluency assessment tool from the top. Only have that welcome message at the beginning. Fix the correction to put the answer into the box. Kid1, I need to do something to get this set up for you.
- On the first page, they continue down a little bit so that any fill-in doesn't get in the way.
- Create a way to exclude some problems in the analysis where she types multiple keys or gets distracted, so the whole data set isn't corrupted by one distracted point. Think about the interaction to do that.
- It's a priority to set this up for a question list so we can keep doing the same sort of problem set to see about progression on it.
- Look at the bug where the user hits the enter key twice.
- Enable a mode where speech detection is enabled and it looks for certain words that you say. Alternatively, provide a way for the parent to input whether to exclude that problem or not.
- Create a way to see a graph of their times for a specific problem when they do it multiple times.
- That's probably a scroll-over thing.
- Fix it saying minus. It's not saying minus for subtraction. Check the other operations.

[] Separate css for analysis, and include quiz css
[] Create table for sessions
    [] display average and max time
    [] display number of problems attempted
    [] display number of incorrect answers
    [] display description of range and operation type
[] Add import sessions and consider session mgmt



### from Kid1 10-15 sessions
[] Add download JSONs on the analysis page
[] Add a pause on the quiz page
[] Fix bug where it stops listening quickly
[] Fix issue with getting two questions in a row
[] Make the start and stop on the listening bigger
[] Investigate and fix glitches with problem numbers 25 to 30 in the big session
[] Change the number in the entry box when doing the override
[] Add the average time for all the questions at the top of the plot.

[x] add sounds
[x] add speech recognition for answer
[] merge in analysis.js
    [x] save jsons in as session objects
    [] see o1 response
[] put math_combo in webflow page

[] make incorrect boxes grayed out in heatmap
[] create way to repeat the last settings, pull from prev json?

## Questions for Clarification

### Database Structure
#### User Data:
- Will there be multiple users in the future?
In the future we'll use authentication and accounts, but that will probably coincide with a migration to a more mature database besides SQLite. So for now, let's go ahead and include the capability to have multiple users in the SQLite file, because we might want to switch between them in the visualization, but it'll just be a few users and we won't actually have accounts associated with them. But I also want to be able to have different SQLite files with different users and sessions, and to be able to combine SQLite files and also to add new JSONs with previous SQLite files.
- Do you need to include user-specific information other than name and ID?
Not now, but in the future we'll collect things like email or age. Actually right now add grade, name, grade and ID.

#### Privacy Concerns:
- Are there any privacy policies or concerns when storing multiple users' data in one database?
No, not now for this phase.

### Problem Identification
#### Problem Variations:
- Should problems with the same numbers but different operations be considered the same or different in the heatmap? For example, is 3 + 4 the same as 4 + 3 in terms of visualization?
Different.

#### Number Range for Heatmap Axes
- Range Limits:
  - What is the maximum number for num1 and num2? Is it fixed (e.g., 0-20), or should it adapt based on the data?
  I want to be able to show these heat maps for the three standard ranges, 0 to 5, 0 to 9, and then 0 to 20. But in general, num1 and num2 can be larger numbers for creating problems and such. It's just for this early progression around arithmetic, I want to focus in on the numbers less than 20. So we don't have to specify how we'll do heat maps or visualization for problem spaces that are larger than 20 right now. Problem spaces with numbers larger than 20, I should say.
- Axis Labels:
  - Should the heatmap include all possible combinations within the range, even if some were never attempted?
  Yes, the heatmaps should be complete and indicate that those combinations were never attempted.

### Visualization Details
#### Heatmap Metrics:
- Do you prefer separate heatmaps for response time and correctness, or combined into one?
So the assumption is in general that she's going to be getting all of the responses correct, and that we're going to be focused on time and to indicate fluency and how immediately available the answers are, or whether she's having to count on her fingers. But we do want to indicate if there are incorrect answers for those combinations. So we should have some way of doing that, such as making them transparent or putting a border around them, like a red border. Let's say use a red border for now to indicate that that combination, that problem has had error responses, answers that were errors.

#### Color Schemes:
- Do you have any preferences for the color palette (e.g., red-to-green for correctness)?
red to green for correctness. I want a slider to control the threshold and color variation.

#### Data Normalization:
- For response times, should the data be normalized or use raw values?
I want a slider to control the threshold and color variation.

#### Annotations:
- Do you want to display the actual values on each cell of the heatmap?
I want the problem to be showed in the cell on the heat map. Even though you can figure out what it is, if I have the rows in the columns which should be labeled, I want it to just show what it is, like "2 + 3".

### Session Selection
#### Default Behavior:
- Should the visualization default to the last session, all sessions, or prompt the user?
I want some user controls for this where you can select all sessions, where you can select last session or last X number of sessions. Let's just include those three options and have it display how many sessions it's showing and what the date range is of those sessions.

#### User Interface:
- How would you like to select sessions? Through command-line inputs, configuration files, or interactive prompts?
Interactive controls - like buttons, selectors, and sliders.

### Additional Features
#### Filtering Options:
- Would you like to filter data based on other criteria, such as operation type or difficulty level?
Yes, I want to be able to filter by operation type but not by difficulty level. Have that be controlled by a pull down selector that shows addition only, subtraction only, addition and subtraction, then multiplication, then division, then multiplication and division, and then exponentiation and then all operations.

#### Aggregated Statistics:
- Are there other metrics you're interested in, such as median response time or standard deviation?
Yes, I want to see the median response time but not the standard deviation.

### Future Considerations
#### Extensibility:
- Should the system be designed to easily incorporate other types of visualizations or analytics in the future?
Yes. The main thing I'm thinking about is what functionality should be implemented in JavaScript, which will be running on the client side versus implemented in Python. And one thing I've been thinking about is using a package called PyGame because I want to be able to include gamification in the future. So I like, you know, what I've seen from that platform and how I could, or that package and how I could use it. I will also likely want to include some voice and some LLM and AI features in the future with both the speech text and text to speech. So there's a lot we can do with it. So. Yeah, I think the main decision now is about what packages to use. So I think for the next response, integrate all of these answers, summarize the specifications, and then present the options for what we can do with packages, which JavaScript libraries and/or PyGame.

#### Integration:
- Do you plan to integrate this tool with other platforms or applications?
Yes, see above answer.


## Updated Plan with Integrated Specifications - with edits

Based on your responses and requirements, here's an updated plan that integrates your decisions and summarizes the specifications:

### Database Structure

Initial implementation in SQLite.

#### Multiple Users in SQLite Database:
- Include multiple users in a single SQLite database.
- Users will have the following fields:
  - user_id (Primary Key)
  - name

#### Flexibility with SQLite Files:
- Capability to add new JSONs to existing SQLite file.

### Problem Identification

#### Distinct Problems in Heatmap:
- Problems with the same numbers but different operations are considered different in the heatmap.
- For example, 3 + 4 is different from 4 + 3.

### Number Range for Heatmap Axes

#### Standard Ranges:
- Focus on standard ranges for early arithmetic progression:
  - 0 to 5
  - 0 to 9
  - 0 to 20

#### Handling Larger Numbers:
- While problems can include numbers larger than 20, heatmaps will currently focus on numbers less than or equal to 20.

#### Complete Heatmaps:
- Heatmaps should include all possible combinations within the selected range, even if some combinations were never attempted.

### Visualization Details

#### Focus on Response Time:
- Assume most answers are correct; focus on response time to indicate fluency.
- Use response time to assess whether answers are immediate or require counting.

#### Indicating Incorrect Answers:
- Use a red border around cells to indicate problems that had incorrect answers.

#### Color Palette and Thresholds:
- Use a red-to-green color palette to represent response times.
- Include a slider to control thresholds and color variation for response times.

#### Cell Annotations:
- Display the problem equation (e.g., "2 + 3") within each cell of the heatmap.
- Rows and columns should be labeled with the corresponding numbers.

#### Median Response Time:
- Display median response time for each problem combination.
- No need to display standard deviation at this time.

### Session Selection

#### User Controls for Session Selection:
- Provide interactive controls to select:
  - All sessions
  - Last session
  - Last N sessions (user can specify N)
- Display the number of sessions included and the date range of those sessions.

### User Interface

Initial implementation in Javascript for web readiness.

#### Interactive Controls:
- Implement interactive controls such as buttons, selectors, and sliders.
- Controls should allow users to adjust visualization parameters in real-time.

### Additional Features

#### Operation Type Filtering:
- Include a pull-down selector to filter by operation type:
  - Addition only
  - Subtraction only
  - Addition and Subtraction
  - Multiplication
  - Division
  - Multiplication and Division
  - Exponentiation
  - All operations

#### Future Data Fields:
- Although not required now, the system should be ready to include additional user-specific information like email or age.

### Future Considerations

#### Extensibility:
- Design the system to easily incorporate other visualizations and analytics in the future.
- Plan for potential integration of gamification features using PyGame.
- Consider future implementation of voice features and AI functionalities, such as speech-to-text and text-to-speech.

#### Integration:
- Plan to integrate this tool with other platforms or applications down the line.

### Integration with Other Tools

#### PyGame:
- Explore using PyGame for future gamification features.
- PyGame can also be used to create custom user interfaces and interactive elements.
