# LEGACY: predecessor CLI/pygame quiz from before the web app. Not maintained —
# the web app (math_quiz.html/.js) is the active surface. record_audio() is a
# placeholder that returns a random answer.
import os
import random
import json
import uuid
import time
import hashlib
import pygame
import sys
import threading
import random
import pyttsx3  # For text-to-speech

### USER AND SETTINGS
def get_user_input_number(prompt, default=None):
    while True:
        user_input = input(prompt)
        if user_input == "" and default is not None:
            return default
        if user_input.isdigit():
            return int(user_input)
        else:
            print("Please enter a valid number.")

def get_username():
    print("Welcome to the Arithmetic Fluency Assessment Tool!")
    return input("Please enter your name: ") or "test"

def get_presets():
    return {
        "t5": {
            "preset": "t5",
            "description": "5 questions adding numbers 0 to 5",
            "note": "",
            "num_problems": 5,
            "number_range": (0, 5),
            "numbers_include": [],
            "numbers_exclude": [],
            "num_numbers": 2,
            "operations": ['+']
        },
        "a9": {
            "preset": "a9",
            "description": "20 questions adding numbers 0 to 9",
            "note": "",
            "num_problems": 20,
            "number_range": (0, 9),
            "numbers_include": [],
            "numbers_exclude": [],
            "num_numbers": 2,
            "operations": ['+']
        }
        # Add more presets here as needed
    }

def get_settings():
    presets = get_presets()
    
    while True:
        preset_input = input("Enter preset ('x' to see available presets or press Enter for custom settings): ")
        if preset_input == "":
            return get_custom_settings()
        elif preset_input == "x":
            print("\nAvailable presets:")
            for key, value in presets.items():
                print(f"  {key}: {value['description']}")
            print()
        elif preset_input in presets:
            selected_preset = presets[preset_input].copy()  # Create a copy to avoid modifying the original
            print(f"\nSelected preset: {selected_preset['description']}")
            note = input("Enter a note for this session (optional): ")
            selected_preset['note'] = note
            return selected_preset
        else:
            print("\nInvalid preset. Please try again.")

def get_custom_settings():
    note = input("Enter a note for this session (optional): ")
    num_problems = get_user_input_number("Enter the number of problems for this session: ", default=5)
    min_range = get_user_input_number("Enter the minimum number in the range: ", default=0)
    max_range = get_user_input_number("Enter the maximum number in the range: ", default=5)
    numbers_include_input = input("Enter numbers to include in one of the numbers (comma-separated, or press Enter for none): ")
    numbers_include = [int(num.strip()) for num in numbers_include_input.split(',') if num.strip().isdigit()] if numbers_include_input else []
    numbers_exclude_input = input("Enter numbers to exclude from all numbers (comma-separated, or press Enter for none): ")
    numbers_exclude = [int(num.strip()) for num in numbers_exclude_input.split(',') if num.strip().isdigit()] if numbers_exclude_input else []
    num_numbers = get_user_input_number("Enter the number of numbers for each problem: ", default=2)
    operations_input = input("Enter the operations to use separated by spaces (+ - * / ^): ").split()
    valid_operations = [op for op in operations_input if op in ['+', '-', '*', '/', '^']]

    if not valid_operations:
        print("No valid operations entered. Defaulting to addition (+).")
        valid_operations = ['+']

    return {
        "preset": "custom",
        "description": "",  # Empty string for custom settings
        "note": note,
        "num_problems": num_problems,
        "number_range": (min_range, max_range),
        "numbers_include": numbers_include,
        "numbers_exclude": numbers_exclude,
        "num_numbers": num_numbers,
        "operations": valid_operations
    }


### QUIZ
def generate_problem(number_range, operations=["+"], numbers_include=None, numbers_exclude=None, num_numbers=2):
    # Generate the main pool of available numbers
    available_numbers = list(range(number_range[0], number_range[1] + 1))
    if numbers_exclude:
        available_numbers = [num for num in available_numbers if num not in numbers_exclude]
    
    if not available_numbers and not numbers_include:
        raise ValueError("No available numbers to generate a problem.")
    
    numbers = []
    
    # Ensure one number is from numbers_include if provided
    if numbers_include:
        numbers.append(random.choice(numbers_include))
    
    # Fill the rest of the numbers from available_numbers
    while len(numbers) < num_numbers:
        numbers.append(random.choice(available_numbers))
    
    # Shuffle the numbers to randomize the position of the included number
    random.shuffle(numbers)
    
    operation = random.choice(operations)
    problem_string = f"{numbers[0]} {operation} {numbers[1]}"
    
    # Replace operation symbols for display
    display_problem = problem_string.replace("**", "^").replace("*", "×").replace("/", "÷")
    
    # Calculate correct answer based on the operation
    if operation == "+":
        correct_answer = sum(numbers)
    elif operation == "-":
        correct_answer = numbers[0] - numbers[1]
    elif operation == "*":
        correct_answer = numbers[0] * numbers[1]
    elif operation == "/":
        correct_answer = numbers[0] / numbers[1]
    elif operation == "^":
        correct_answer = numbers[0] ** numbers[1]
    else:
        raise ValueError(f"Unsupported operation: {operation}")
    
    return display_problem, correct_answer

def assign_problem_id(problem_text):
    # Generate an MD5 hash of the problem text
    hash_object = hashlib.md5(problem_text.encode())
    problem_hash = hash_object.hexdigest()[:16]  # Use the first 16 hex characters
    return problem_hash

def write_session_json(session_data, folder_path='apps/math-quiz/math-quiz_data'):
    filename = f"math_session_{session_data['user']['name']}_{session_data['session']['start_time']}.json"
    filepath = os.path.join(folder_path, filename)
    os.makedirs(folder_path, exist_ok=True)
    with open(filepath, 'w') as json_file:
        json.dump(session_data, json_file, indent=2)
    print(f"\nSession data saved to {filepath}")

def display_summary(session_summary, incorrect_problems):
    print("Session Summary:")
    print(f"Total problems attempted: {session_summary['total_problems']}")
    print(f"Number of correct answers: {session_summary['correct_answers']}")
    print(f"Average response time ms: {session_summary['average_response_time_ms']}")
    print(f"Total test time: {session_summary['total_test_time']}")
    if incorrect_problems:
        print("Incorrectly answered problems:")
        for p in incorrect_problems:
            print(f"{p['problem_text']} (Your answer: {p['user_answer']}, Correct answer: {p['correct_answer']})")
    else:
        print("All answers were correct!")

def get_current_datetime_filefriendly():
    """Return local system time formatted like the web app's session timestamps (YYYY-MM-DD_HHMMSS).
    Same format as core/fileops.py get_current_datetime_filefriendly(include_utc=False), kept local
    so this app has no dependency on core/ (core pins to America/Los_Angeles; this uses system time)."""
    return time.strftime("%Y-%m-%d_%H%M%S")
def run_assessment(settings, username):
    # Initialize session data
    session_id = str(uuid.uuid4())
    session_start_time = get_current_datetime_filefriendly()
    problems_attempted = []
    used_problems = set()

    print("\nStarting the assessment...\n")
    print("Enter 'x' at any time to quit and save progress.\n")

    for problem_num in range(settings['num_problems']):
        # Generate a unique problem
        max_attempts = 100  # Maximum number of attempts to generate a unique problem
        for attempt in range(max_attempts):
            display_problem, correct_answer = generate_problem(
                number_range=settings['number_range'],
                operations=settings['operations'],
                numbers_include=settings['numbers_include'],
                numbers_exclude=settings['numbers_exclude'],
                num_numbers=settings['num_numbers']
            )
            problem_id = assign_problem_id(display_problem)
            if problem_id not in used_problems:
                used_problems.add(problem_id)
                break
        # If we couldn't generate a unique problem, use the last generated one anyway
        
        print(f"Solve: {display_problem}")
        start_time = time.time()
        user_answer_string = input("Your answer: ")
        end_time = time.time()

        if user_answer_string.lower() == 'x':
            print("\nQuitting early. Saving progress...")
            break

        # Input validation
        try:
            user_answer_numeric = float(user_answer_string)
            user_answer_int = int(user_answer_numeric)
            is_correct = abs(user_answer_numeric - correct_answer) < 1e-6
        except ValueError:
            print("Invalid input. Please enter a number.")
            is_correct = False
            user_answer_numeric = None
            user_answer_int = None

        response_time_ms = round((end_time - start_time) * 1000)

        if is_correct:
            print("Correct!\n")
        else:
            print(f"Incorrect. The correct answer was {correct_answer}.\n")

        # Record problem data
        problem_data = {
            "id": problem_id,
            "problem_text": display_problem,
            "correct_answer": correct_answer,
            "user_answer_string": user_answer_string,
            "user_answer": user_answer_int,
            "is_correct": is_correct,
            "response_time_ms": response_time_ms
        }
        problems_attempted.append(problem_data)

    # Update the number of problems in settings
    settings['num_problems'] = len(problems_attempted)

    # Session end
    session_end_time = get_current_datetime_filefriendly()
    total_problems = len(problems_attempted)
    correct_answers = sum(1 for p in problems_attempted if p["is_correct"])
    average_response_time_ms = sum(p["response_time_ms"] for p in problems_attempted) / total_problems if total_problems > 0 else 0
    incorrect_problems = [p for p in problems_attempted if not p["is_correct"]]

    # Calculate total test time
    start_time = time.strptime(session_start_time, "%Y-%m-%d_%H%M%S")
    end_time = time.strptime(session_end_time, "%Y-%m-%d_%H%M%S")
    total_seconds = time.mktime(end_time) - time.mktime(start_time)
    total_minutes, remaining_seconds = divmod(round(total_seconds), 60)
    total_test_time = f"{total_minutes}:{remaining_seconds:02d}"

    # Prepare session summary
    session_summary = {
        "total_problems": total_problems,
        "correct_answers": correct_answers,
        "average_response_time_ms": round(average_response_time_ms),
        "total_test_time": total_test_time
    }

    # Display summary
    display_summary(session_summary, incorrect_problems)

    # Prompt for additional note
    additional_note = input("\nAdd anything to the note? (Press Enter for none): ")
    if additional_note:
        if settings['note']:
            settings['note'] += f", POST QUIZ: {additional_note}"
        else:
            settings['note'] = f"POST QUIZ: {additional_note}"

    # Prepare JSON data
    session_data = {
        "version": "1.0",
        "user": {
            "name": username
        },
        "session": {
            "id": session_id,
            "start_time": session_start_time,
            "end_time": session_end_time,
            "settings": settings,
            "summary": session_summary,
            "problems": problems_attempted
        }
    }

    # Write JSON data to file
    write_session_json(session_data)

def manual_tests():
     # Test generate_problem function
    print("Testing generate_problem function:")
    number_range = list(range(1, 11))
    operations = ["+"]
    
    print("Test 1: Basic addition")
    problem, answer = generate_problem(number_range, operations)
    print(f"Problem: {problem}, Answer: {answer}")
    
    print("\nTest 2: With numbers_include")
    problem, answer = generate_problem(number_range, operations, numbers_include=[15, 20])
    print(f"Problem: {problem}, Answer: {answer}")
    
    print("\nTest 3: With numbers_exclude")
    problem, answer = generate_problem(number_range, operations, numbers_exclude=[1, 2, 3])
    print(f"Problem: {problem}, Answer: {answer}")
    
    # Test assign_problem_id function
    print("\nTesting assign_problem_id function:")
    
    print("Test 1: Simple addition")
    problem_id = assign_problem_id("5 + 3")
    print(f"Problem: 5 + 3, ID: {problem_id}")
    
    print("\nTest 2: Multiplication")
    problem_id = assign_problem_id("4 × 6")
    print(f"Problem: 4 × 6, ID: {problem_id}")
    
    print("\nTest 3: Complex problem")
    problem_id = assign_problem_id("2 + 3 + 4")
    print(f"Problem: 2 + 3 + 4, ID: {problem_id}")


## PYGAME
# Text-to-speech function
def text_to_speech(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

# Placeholder function for audio recording and transcription
def record_audio():
    # Replace this with your DeepGram API integration
    print("Recording audio... (placeholder)")
    time.sleep(3)  # Simulate recording duration
    # Simulate transcribed answer
    user_answer = random.randint(0, 18)  # Random answer for testing
    print(f"User said: {user_answer}")
    return user_answer

# New function for manual input
def manual_input():
    user_input = input("Enter your answer: ")
    try:
        return int(user_input)
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None

# Main function with Pygame integration
def main(settings, username, input_method='manual'):
    pygame.init()
    screen_width = 800
    screen_height = 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Math Quiz")

    font_large = pygame.font.SysFont(None, 72)
    font_medium = pygame.font.SysFont(None, 48)
    font_small = pygame.font.SysFont(None, 36)

    clock = pygame.time.Clock()

    # Main loop variables
    running = True
    problem_active = False
    countdown_active = False
    countdown_colors = ['red', 'yellow', 'green']
    countdown_index = 0
    countdown_timer = 0
    problem_start_time = 0

    # Prepare colors
    colors = {
        'white': (255, 255, 255),
        'black': (0, 0, 0),
        'red': (255, 0, 0),
        'yellow': (255, 255, 0),
        'green': (0, 255, 0)
    }

    # Problem variables
    problem_id = None
    problem_text = ""
    correct_answer = None
    user_answer = None
    response_time_ms = None

    # Session data
    problems_attempted = []
    session_id = str(uuid.uuid4())
    session_start_time = time.time()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not countdown_active and not problem_active:
                    # Start countdown
                    countdown_active = True
                    countdown_index = 0
                    countdown_timer = time.time()
                    print("Starting countdown...")

        screen.fill(colors['white'])

        if countdown_active:
            # Handle countdown
            elapsed_time = time.time() - countdown_timer
            if elapsed_time >= 1:
                countdown_timer = time.time()
                if countdown_index < len(countdown_colors):
                    color_name = countdown_colors[countdown_index]
                    color = colors[color_name]
                    # Draw countdown light
                    pygame.draw.circle(screen, color, (screen_width // 2, screen_height // 2), 50)
                    countdown_index += 1
                    print(f"{color_name.capitalize()} light")
                else:
                    # Countdown finished, show problem
                    countdown_active = False
                    problem_active = True
                    # Generate problem
                    problem_text, correct_answer = generate_problem(
                        number_range=settings['number_range'],
                        operations=settings['operations'],
                        numbers_include=settings['numbers_include'],
                        numbers_exclude=settings['numbers_exclude'],
                        num_numbers=settings['num_numbers']
                    )
                    problem_id = assign_problem_id(problem_text)
                    # Read the problem aloud
                    threading.Thread(target=text_to_speech, args=(problem_text,)).start()
                    # Start recording audio
                    threading.Thread(target=record_audio_thread, args=(lambda ans: setattr(sys.modules[__name__], 'user_answer', ans),)).start()
                    # Record the start time
                    problem_start_time = time.time()

        elif problem_active:
            # Display the problem
            problem_surface = font_large.render(problem_text, True, colors['black'])
            problem_rect = problem_surface.get_rect(center=(screen_width // 2, screen_height // 2))
            screen.blit(problem_surface, problem_rect)

            if input_method == 'audio':
                # Start recording audio
                if user_answer is None:
                    threading.Thread(target=record_audio_thread, args=(lambda ans: setattr(sys.modules[__name__], 'user_answer', ans),)).start()
            else:  # manual input
                # Display prompt for manual input
                input_prompt = font_small.render("Type your answer and press Enter", True, colors['black'])
                input_rect = input_prompt.get_rect(center=(screen_width // 2, screen_height // 2 + 50))
                screen.blit(input_prompt, input_rect)

            # Check if user_answer is available
            if user_answer is not None:
                response_time_ms = int((time.time() - problem_start_time) * 1000)
                is_correct = (user_answer == correct_answer)
                if is_correct:
                    result_text = "Correct!"
                else:
                    result_text = f"Incorrect. The correct answer was {correct_answer}."

                # Record problem data
                problem_data = {
                    "id": problem_id,
                    "problem_text": problem_text,
                    "correct_answer": correct_answer,
                    "user_answer": user_answer,
                    "is_correct": is_correct,
                    "response_time_ms": response_time_ms
                }
                problems_attempted.append(problem_data)

                print(f"Problem: {problem_text}")
                print(f"User Answer: {user_answer}")
                print(f"Correct Answer: {correct_answer}")
                print(f"Response Time: {response_time_ms} ms")
                print(result_text)

                # Reset for next problem
                problem_active = False
                user_answer = None

        else:
            # Waiting for user to press space bar
            prompt_surface = font_medium.render("Press SPACE to start the next problem", True, colors['black'])
            prompt_rect = prompt_surface.get_rect(center=(screen_width // 2, screen_height // 2))
            screen.blit(prompt_surface, prompt_rect)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

    # After quitting, save the session data
    session_end_time = time.time()
    session_summary = {
        "total_problems": len(problems_attempted),
        "correct_answers": sum(1 for p in problems_attempted if p["is_correct"]),
        "average_response_time_ms": sum(p["response_time_ms"] for p in problems_attempted) / len(problems_attempted),
        "total_test_time": session_end_time - session_start_time
    }
    
    session_data = {
        "user": {
            "name": username
        },
        "session": {
            "id": session_id,
            "start_time": session_start_time,
            "end_time": session_end_time,
            "settings": settings,
            "summary": session_summary,
            "problems": problems_attempted
        }
    }

    write_session_json(session_data)
    
    print("Session ended.")
    display_summary(session_summary, [p for p in problems_attempted if not p["is_correct"]])

def record_audio_thread(callback):
    user_answer = record_audio()
    # Pass the user_answer back to the main thread
    callback(user_answer)

# New function to handle manual input in a separate thread
def manual_input_thread(callback):
    user_answer = manual_input()
    # Pass the user_answer back to the main thread
    callback(user_answer)

if __name__ == "__main__":
    username = get_username()
    settings = get_settings()
    # run_assessment(settings, username)

    input_method = 'manual'  # Change this to 'audio' when you want to test audio input
    main(settings, username, input_method)

