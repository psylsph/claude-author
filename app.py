import autogen
from typing import List, Dict
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from json_repair import json_repair
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem.porter import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config import get_config
import re
import os

words_per_chapter = 3000
num_chapters = 15
outline_only = True

def initialize_characters(self, premise: str):
    """Extract and initialize characters from the premise."""
    character_file = "novel_output/characters.json"

    # Check if the character file already exists
    if os.path.exists(character_file):
        with open(character_file, "r") as f:
            characters_data = json.load(f)
            self.character_manager.from_dict(characters_data)
            print("Characters loaded from existing file.")
            return

    chat_manager = autogen.GroupChat(
        agents=[self.user_proxy, self.character_agent],
        messages=[],
        max_round=3,
        speaker_selection_method="round_robin",
        allow_repeat_speaker=False
    )

    manager = autogen.GroupChatManager(groupchat=chat_manager)

    # Use string formatting to safely insert premise
    prompt = """Based on this premise: '{}'

    Create detailed character profiles in JSON format for each character. The response should be a JSON array where each character is an object with these fields:
    - name: string
    - role: string
    - description: string
    - personality: string
    - relationships: object mapping character names to relationship descriptions
    - key_traits: array of strings
    - first_appearance: string (chapter number)
    - story_arc: string

    Example format:
    ```json
    [
        {
            "name": "John Doe",
            "role": "Protagonist",
            "description": "A tall man with brown hair...",
            "personality": "Brave but reckless...",
            "relationships": {
                "Jane Smith": "Love interest",
                "Bob Johnson": "Best friend"
            },
            "key_traits": ["courageous", "stubborn", "loyal"],
            "first_appearance": "1",
            "story_arc": "Grows from reckless youth to responsible leader"
        }
    ]
    ```

    Create profiles for all major and significant supporting characters.
    End with TERMINATE""".format(premise)

    self.user_proxy.initiate_chat(
        manager,
        message=prompt
    )

    # Parse the character profiles from the response
    try:
        response = chat_manager.messages[1]["content"]

        # Extract JSON from code blocks
        json_match = re.search(r'```json(.*?)```', response, re.DOTALL)
        if json_match:
            striped_json = json_match.group(1).strip()
        else:
            striped_json = response

        striped_json = striped_json.replace("\n", "")
        striped_json = striped_json.replace("TERMINATE", "")
        try:
            characters = json_repair.loads(striped_json)
            for char_data in characters:
                # Add last_appearance field (will be updated as the story progresses)
                char_data['last_appearance'] = char_data['first_appearance']

                # Create and add the character
                if char_data['name']:  # Only add if we have at least a name
                    try:
                        character = Character(**char_data)
                        self.character_manager.add_character(character)
                        print(f"Added character: {char_data['name']}")
                    except Exception as e:
                        print(f"Error creating character {char_data['name']}: {e}")
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON character data: {e}")
            print("Response was:", response)
            exit(1)

    except Exception as e:
        print(f"Error parsing character data: {e}")
        print("Response was:", response)
        exit(1)

    # Save the characters to a file
    with open(character_file, "w") as f:
        json.dump(self.character_manager.to_dict(), f, indent=2, separators=(',', ': '))
        f.flush()

def write_novel(self, premise: str, num_chapters: int) -> Dict[str, str]:
    """Generate a complete novel based on the premise and number of chapters."""
    self.initialize_characters(premise)

    novel = {
        "metadata": {
            "premise": premise,
            "created_date": datetime.now().isoformat(),
            "num_chapters": num_chapters
        },
        "characters": self.character_manager.to_dict(),
        "chapters": {}
    }

    for chapter_num in range(1, num_chapters + 1):
        print(f"\nWorking on Chapter {chapter_num}...")

        # Check if the outline already exists
        outline_file = f"novel_output/outline_chapter_{chapter_num}.txt"
        if os.path.exists(outline_file):
            with open(outline_file, "r") as f:
                outline = f.read()
        else:
            # Generate chapter outline
            outline = self.generate_chapter_outline(premise, chapter_num)

        # Write chapter with revisions
        chapter_versions = self.write_chapter_with_revisions(outline, chapter_num)

        # Store chapter and its metadata
        novel[f"Chapter_{chapter_num}"] = {
            "outline": outline,
            "versions": chapter_versions,
            # Use the last revision as the final version
            "final_version": chapter_versions[f"revision_{len(chapter_versions)}"]["content"]
        }

        # Update character tracking data
        novel["characters"] = self.character_manager.to_dict()

        # Save progress after each chapter
        with open(f"novel_output/novel_progress.json", "w") as f:
            json.dump(novel, f, indent=2, separators=(',', ': '))
            f.flush()

    return novel


class OutlineReviewer:
    def __init__(self):
        self.outlines = {}  # Store chapter outlines for comparison
        self.titles = set()  # Store chapter titles

    def add_existing_outline(self, outline: str, chapter_num: int):
        """Add existing outlines to the reviewer"""
        self.outlines[chapter_num] = outline
        title = self.extract_title(outline)
        if title:
            self.titles.add(title)

    def _preprocess(self, text):
        """Preprocesses the text by removing non-alphabetic characters, stop words, and stemming the words."""
        stop_words = set(stopwords.words('english'))
        stemmer = PorterStemmer()

        tokens = word_tokenize(text.lower())
        tokens = [stemmer.stem(token) for token in tokens if token.isalpha() and token not in stop_words]

        return ' '.join(tokens)


    def _calculate_similarity(self, text1, text2):
        """Calculates the cosine similarity score between two texts using TF-IDF."""
        texts = [self._preprocess(text1), self._preprocess(text2)]
        vectorizer = TfidfVectorizer()
        tfidf = vectorizer.fit_transform(texts)

        return cosine_similarity(tfidf)[0][1]
    
    def validate_outline(self, outline: str, previous_outlines: List[str] = None) -> bool:
        """Check if outline is unique compared to previous outlines using similarity metrics"""
        if not previous_outlines:
            return True

        nltk.download('stopwords')
        nltk.download('punkt_tab')
        nltk.download('wordnet')

        for prev_outline in previous_outlines:
            similarity = self._calculate_similarity( outline.lower(), prev_outline.lower())
            if similarity > 0.7:  # If more than 70% similar, consider it too close
                return False
        return True

    def extract_title(self, outline: str) -> str:
        """Extract chapter title from outline"""
        # Look for common title patterns
        import re
        title_patterns = [
            r'Title:\s*"([^"]+)"',
            r'Title:\s*(.+)(?:\n|$)',
            r'Chapter\s+\d+:\s*(.+)(?:\n|$)',
            r'#\s*(.+)(?:\n|$)'
        ]

        for pattern in title_patterns:
            match = re.search(pattern, outline)
            if match:
                return match.group(1).strip()
        return ""

    def check_title_uniqueness(self, title: str) -> bool:
        """Check if chapter title is unique"""
        return title.lower() not in {t.lower() for t in self.titles}

    def review_outline(self, outline: str, chapter_num: int, premise: str) -> Dict:
        """Review outline for consistency, uniqueness, and alignment with premise"""
        title = self.extract_title(outline)
        previous_outlines = list(self.outlines.values())

        review = {
            "is_valid": True,
            "title_unique": True,
            "outline_unique": True,
            "issues": [],
            "suggestions": []
        }

        # Check title uniqueness
        if title:
            review["title_unique"] = self.check_title_uniqueness(title)
            if not review["title_unique"]:
                review["issues"].append(f"Chapter title '{title}' is too similar to an existing title")

        # Check outline uniqueness
        review["outline_unique"] = self.validate_outline(outline, previous_outlines)

        if not review["outline_unique"]:
            review["issues"].append("Outline is too similar to a previous chapter")


        # Update stored data if outline is valid
        if not review["issues"]:
            self.outlines[chapter_num] = outline
            if title:
                self.titles.add(title)

        review["is_valid"] = not review["issues"]
        return review

@dataclass
class Character:
    name: str
    role: str
    description: str
    personality: str
    relationships: Dict[str, str]
    key_traits: List[str]
    first_appearance: str  # Chapter number
    last_appearance: str   # Chapter number
    story_arc: str

class CharacterManager:
    def __init__(self):
        self.characters = {}
        self.mentions = {}  # Track character mentions by chapter

    def add_character(self, character: Character):
        try:
            int(character.first_appearance)
        except ValueError:
            character.first_appearance = 0
            character.last_appearance = 0
        self.characters[character.name.lower()] = character

    def get_character(self, name: str) -> Character:
        return self.characters.get(name.lower())

    def update_appearance(self, name: str, chapter: str):
        char = self.get_character(name.lower())
        if char:
            if not char.first_appearance:
                char.first_appearance = chapter
            char.last_appearance = chapter

    def track_mention(self, chapter: str, name: str):
        if chapter not in self.mentions:
            self.mentions[chapter] = {}
        name_lower = name.lower()
        self.mentions[chapter][name_lower] = self.mentions[chapter].get(name_lower, 0) + 1

    def to_dict(self):
        return {
            "characters": {name: asdict(char) for name, char in self.characters.items()},
            "mentions": self.mentions
        }

    def from_dict(self, data: Dict):
        self.characters = {
            name: Character(**char_data)
            for name, char_data in data["characters"].items()
        }
        self.mentions = data["mentions"]

# Configure the agents
llm_config = get_config()

class NovelWriter:
    def __init__(self, max_revisions=2):

        self.character_manager = CharacterManager()
        self.outline_reviewer = OutlineReviewer()

        # Initialize the agents
        self.character_agent = autogen.AssistantAgent("character_manager",
            system_message="""You are a character consistency manager who:
1. Tracks all characters and their attributes
2. Ensures character names, traits, and behaviors remain consistent
3. Flags any inconsistencies in character portrayal
4. Maintains character relationships and development arcs
5. Provides character information to other agents
Be thorough and specific in maintaining character consistency.""",
            llm_config=llm_config
        )
        # Initialize the agents
        self.editor = autogen.AssistantAgent("editor",
            system_message="""You are a skilled book editor who:
1. Reviews story premises and provides constructive feedback
2. Ensures plot consistency and character development
3. Maintains the overall narrative structure
4. Provides detailed chapter outlines Please be constructive and specific in your feedback.""",
            llm_config=llm_config )
        self.writer = autogen.AssistantAgent("writer",
            system_message="""You are a creative writer who:
1. Transforms outlines into engaging prose
2. Creates vivid descriptions and natural dialogue
3. Maintains consistent character voices
4. Follows the established plot structure while adding creative details Write in a clear, engaging style without excessive description.
5. Incorporates feedback to improve chapters""",
            llm_config=llm_config )
        self.reviewer = autogen.AssistantAgent("reviewer",
            system_message="""You are a literary critic who:
1. Reviews completed chapters for quality and consistency
2. Suggests improvements for pacing and style
3. Identifies potential plot holes or character inconsistencies
4. Ensures each chapter advances the story meaningfully Provide specific, actionable feedback.""",
            llm_config=llm_config )
        self.user_proxy = autogen.UserProxyAgent(name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config={"work_dir": "novel_output"}, )
        self.max_revisions = max_revisions

    def initialize_characters(self, premise: str):
        """Extract and initialize characters from the premise."""
        character_file = "novel_output/characters.json"
    
        # Check if the character file already exists
        if os.path.exists(character_file):
            with open(character_file, "r", encoding="UTF-8") as f:
                characters_data = json.load(f)
                self.character_manager.from_dict(characters_data)
                print("Characters loaded from existing file.\n")
                return
    
        chat_manager = autogen.GroupChat(
            agents=[self.user_proxy, self.character_agent],
            messages=[],
            max_round=3,
            speaker_selection_method="round_robin",
            allow_repeat_speaker=False
        )
    
        manager = autogen.GroupChatManager(groupchat=chat_manager)
    
        # Use string formatting to safely insert premise
        prompt = """Based on this premise: '{}'
    
        Create detailed character profiles in JSON format for each character. The response should be a JSON array where each character is an object with these fields:
        - name: string
        - role: string
        - description: string
        - personality: string
        - relationships: object mapping character names to relationship descriptions
        - key_traits: array of strings
        - first_appearance: string (chapter number)
        - story_arc: string
    
        Example format:
        ```json
        [
            {{
                "name": "John Doe",
                "role": "Protagonist",
                "description": "A tall man with brown hair...",
                "personality": "Brave but reckless...",
                "relationships": {{
                    "Jane Smith": "Love interest",
                    "Bob Johnson": "Best friend"
                }},
                "key_traits": ["courageous", "stubborn", "loyal"],
                "first_appearance": "1",
                "story_arc": "Grows from reckless youth to responsible leader"
            }}
        ]
        ```
    
        Create profiles for all major and significant supporting characters.
        End with TERMINATE""".format(premise)
    
        self.user_proxy.initiate_chat(
            manager,
            message=prompt
        )
    
        # Parse the character profiles from the response
        try:
            response = chat_manager.messages[1]["content"]
    
            # Extract JSON from code blocks
            json_match = re.search(r'```json(.*?)```', response, re.DOTALL)
            if json_match:
                striped_json = json_match.group(1).strip()
            else:
                striped_json = response
    
            striped_json = striped_json.replace("\n", "")
            striped_json = striped_json.replace("TERMINATE", "")
            try:
                characters = json_repair.loads(striped_json)
                for char_data in characters:
                    # Add last_appearance field (will be updated as the story progresses)
                    char_data['last_appearance'] = char_data['first_appearance']
    
                    # Create and add the character
                    if char_data['name']:  # Only add if we have at least a name
                        try:
                            character = Character(**char_data)
                            self.character_manager.add_character(character)
                            print(f"Added character: {char_data['name']}")
                        except Exception as e:
                            print(f"Error creating character {char_data['name']}: {e}")
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON character data: {e}")
                print("Response was:", response)
                exit(1)
    
        except Exception as e:
            print(f"Error parsing character data: {e}")
            print("Response was:", response)
            exit(1)
    
        # Save the characters to a file
        with open(character_file, "w", encoding="UTF-8") as f:
            json.dump(self.character_manager.to_dict(), f, indent=2, separators=(',', ': '))
            f.flush()

    def get_character_context(self, chapter_num: int) -> str:
        """Get current character context for the chapter."""
        relevant_chars = {
            name: char for name, char in self.character_manager.characters.items()
            if (not char.last_appearance or  # New characters
                int(re.sub(r'[^0-9]', '', char.last_appearance)) >= chapter_num - 2)  # Recently appeared characters
        }

        context = "Current Character Profiles:\n\n"
        for char in relevant_chars.values():
            context += f"""
            Name: {char.name}
            Role: {char.role}
            Description: {char.description}
            Key Traits: {', '.join(char.key_traits)}
            Recent Activity: Last appeared in Chapter {char.last_appearance or 'N/A'}

            """
        return context

    def review_outline_with_agents(self, outline: str, chapter_num: int, premise: str) -> tuple:
        """Have agents review the outline for consistency and quality"""
        chat_manager = autogen.GroupChat(
            agents=[self.user_proxy, self.editor, self.character_agent],
            messages=[],
            max_round=3,
            speaker_selection_method="round_robin",  # Added this parameter
            allow_repeat_speaker=False  # Added this parameter
        )

        manager = autogen.GroupChatManager(groupchat=chat_manager)

        character_context = self.get_character_context(chapter_num)

        prompt = f"""Review this outline for Chapter {chapter_num}:

{outline}

Original Premise:
{premise}

Character Context:
{character_context}

Evaluate the outline for:
1. Consistency with previous chapters and premise
2. Character development and proper use
3. Plot progression
4. Unique story elements
5. Pacing and structure

Editor: Please review the plot and structure.
Character Manager: Please review character consistency and development.

Provide specific feedback and suggestions.
End with TERMINATE"""

        self.user_proxy.initiate_chat(
            manager,
            message=prompt
        )

        agent_feedback = chat_manager.messages[1]["content"]

        # Also run automated checks
        automated_review = self.outline_reviewer.review_outline(outline, chapter_num, premise)

        return agent_feedback, automated_review

    def generate_chapter_outline(self, premise: str, chapter_num: int) -> str:
        """Generate an outline for a specific chapter based on the premise."""
        max_attempts = 3

        if chapter_num == num_chapters:
            extra_instructions = "This is the final chapter. Ensure a satisfying conclusion."

        for attempt in range(max_attempts):
            # Generate initial outline
            character_context = self.get_character_context(chapter_num)

            chat_manager = autogen.GroupChat(
                agents=[self.user_proxy, self.editor, self.character_agent],
                messages=[],
                max_round=3,
                speaker_selection_method="round_robin",
                allow_repeat_speaker=False
            )

            manager = autogen.GroupChatManager(groupchat=chat_manager)

            prompt = f"""Based on the following premise: '{premise}'

Character Context:
{character_context}

{extra_instructions}

Create a detailed outline for Chapter {chapter_num} of {num_chapters}. Include:
1. A unique and descriptive chapter title
2. Key plot points
3. Character appearances and interactions
4. Setting descriptions
5. Major events or revelations

Ensure all character appearances and actions align with their established profiles.
The chapter's content MUST be unique compared to previous chapters.
Respond in a structured format suitable for the writer to develop into prose.

Start with the chapter title in the format 'Title: "Chapter Title"'"""

            self.user_proxy.initiate_chat(
                manager,
                message=prompt
            )

            outline = chat_manager.messages[1]["content"]

            # Review the outline
            agent_feedback, automated_review = self.review_outline_with_agents(outline, chapter_num, premise)

            if automated_review["is_valid"]:
                print(f"Outline for Chapter {chapter_num} approved on attempt {attempt + 1}")
                return outline
            else:
                print(f"\nOutline issues detected in attempt {attempt + 1}:")
                for issue in automated_review["issues"]:
                    print(f"- {issue}")

                if attempt < max_attempts - 1:
                    print("Generating new outline...")
                    # Add feedback for next generation attempt
                    chat_manager.messages.append({
                        "role": "user",
                        "content": f"""Previous outline had these issues:
                        {', '.join(automated_review['issues'])}

                        Agent feedback:
                        {agent_feedback}

                        Please generate a new outline addressing these issues."""
                    })
                else:
                    print("Maximum outline generation attempts reached. Using best version.")
                    return outline

    def write_chapter(self, outline: str, chapter_num: int, previous_feedback: str = None) -> str:
        """Transform a chapter outline into prose, incorporating any previous feedback."""

        character_context = self.get_character_context(chapter_num)
        chat_manager = autogen.GroupChat( agents=[self.user_proxy, self.writer], messages=[], max_round=5,
                                                     speaker_selection_method="round_robin", allow_repeat_speaker=False)
        manager = autogen.GroupChatManager(groupchat=chat_manager)

        feedback_prompt = ""
        if previous_feedback:
            feedback_prompt = f"\nPlease address this feedback in your revision:\n{previous_feedback}"

        prompt = f"""Using this outline for Chapter {chapter_num} of {num_chapters}, write a complete chapter in engaging prose:

{outline}

Character Context:
{character_context}
Editor Feedback:
{feedback_prompt}

Focus on:
1. Natural dialogue and character interactions
2. Vivid but concise descriptions
3. Smooth scene transitions
4. Maintaining consistent pacing Write the chapter now
5. Each chapter MUST contain at least {words_per_chapter} words
6. Each chapter MUST be self-contained and complete, while advancing the overall story
Write the chapter now, ending with the word TERMINATE
"""

        self.user_proxy.initiate_chat( manager, message=prompt)
        chapter_content = chat_manager.messages[1]["content"]
        self._update_character_appearances(chapter_content, str(chapter_num))
        # Extract the last message from the writer as the chapter
        return chapter_content

    def _update_character_appearances(self, content: str, chapter: str):
        """Update character appearances based on chapter content."""
        for char_name in self.character_manager.characters.keys():
            if char_name.lower() in content.lower():
                self.character_manager.update_appearance(char_name, chapter)
                self.character_manager.track_mention(chapter, char_name)

    def review_chapter(self, chapter: str, chapter_num: int, revision_num: int) -> str:
        """Review a written chapter and provide feedback."""
        character_context = self.get_character_context(chapter_num)
        chat_manager = autogen.GroupChat(
            agents=[self.user_proxy, self.reviewer, self.character_agent],
            messages=[],
            max_round=3,
            speaker_selection_method="round_robin",
            allow_repeat_speaker=False
        )

        manager = autogen.GroupChatManager(groupchat=chat_manager)

        prompt = f"""Review this draft (revision {revision_num}) of Chapter {chapter_num}:

{chapter}

Character Context:
{character_context}

Provide specific feedback on:
1. Plot progression and pacing
2. Character development
3. Writing style and dialogue
4. Areas for improvement
5. The number of words, the writer should aiming for at least {words_per_chapter} words per chapter

Pay special attention to character consistency issues.
If this is revision {revision_num}, be extra thorough in your assessment.
End your review with TERMINATE"""

        self.user_proxy.initiate_chat(
            manager,
            message=prompt
        )
        return chat_manager.messages[1]["content"]

    def write_chapter_with_revisions(self, outline: str, chapter_num: int) -> Dict[str, str]:
        """Write a chapter with multiple revisions based on feedback."""
        chapter_versions = {}
        current_feedback = None

        for revision in range(self.max_revisions):
            print(f"\nWorking on Chapter {chapter_num}, Revision {revision + 1}...")

            # Write chapter (incorporating previous feedback if it exists)
            chapter = self.write_chapter(outline, chapter_num, current_feedback)

            # Get feedback on the chapter
            current_feedback = self.review_chapter(chapter, chapter_num, revision + 1)

            # Store this version
            chapter_versions[f"revision_{revision + 1}"] = {
                "content": chapter,
                "feedback": current_feedback
            }

            # Check if the feedback indicates major issues
            if "excellent" in current_feedback.lower() or "outstanding" in current_feedback.lower():
                print(f"Chapter {chapter_num} achieved satisfactory quality after {revision + 1} revisions.")
                break

        return chapter_versions

    def write_novel(self, premise: str, num_chapters: int) -> Dict[str, str]:
        """Generate a complete novel based on the premise and number of chapters."""
        self.initialize_characters(premise)

        novel = {
            "metadata": {
                "premise": premise,
                "created_date": datetime.now().isoformat(),
                "num_chapters": num_chapters
            },
            "characters": self.character_manager.to_dict(),
            "chapters": {}
        }

        for chapter_num in range(1, num_chapters + 1):
            print(f"\nStarting work on Chapter {chapter_num}...")

            # Check if the outline already exists
            outline_file = f"novel_output/outline_chapter_{chapter_num}.txt"
            if os.path.exists(outline_file):
                print(f"Outline for Chapter {chapter_num} already exists. Loading...")
                with open(outline_file, "r", encoding="UTF-8") as f:
                    outline = f.read()
                self.outline_reviewer.add_existing_outline( outline, chapter_num)
            else:
                # Generate chapter outline
                outline = self.generate_chapter_outline(premise, chapter_num)
                # Save the outline to a file
                with open(outline_file, "w", encoding="UTF-8") as f:
                    f.write(outline)

            if not outline_only:
                # Write chapter with revisions
                chapter_versions = self.write_chapter_with_revisions(outline, chapter_num)

                # Store chapter and its metadata
                novel[f"Chapter_{chapter_num}"] = {
                    "outline": outline,
                    "versions": chapter_versions,
                    # Use the last revision as the final version
                    "final_version": chapter_versions[f"revision_{len(chapter_versions)}"]["content"]
                }

                # Update character tracking data
                novel["characters"] = self.character_manager.to_dict()

                # Save progress after each chapter
                with open(f"novel_output/novel_progress.json", "w", encoding="UTF-8") as f:
                    json.dump(novel, f, indent=2, separators=(',', ': '))
                    f.flush()

        return novel

def main():
    # Create the novel_output directory if it doesn't exist
    import os
    os.makedirs("novel_output", exist_ok=True)
    # Example usage
    novel_writer = NovelWriter(max_revisions=3)
    premise = open("ideas/unit985.md", "r", encoding="UTF-8").read()
    
    novel = novel_writer.write_novel(premise, num_chapters)
    # Save the complete novel
    with open("novel_output/final_novel.json", "w", encoding="UTF-8") as f:
        json.dump(novel, f, indent=2, separators=(',', ': '))

    # Create a readable text version
    with open("novel_output/final_novel.txt", "w", encoding="UTF-8") as f:
        # Write premise and character information
        f.write("Novel Premise:\n")
        f.write("=" * 50 + "\n")
        f.write(novel["metadata"]["premise"] + "\n\n")

        f.write("Characters:\n")
        f.write("=" * 50 + "\n")
        for char in novel["characters"]["characters"].values():
            f.write(f"\n{char['name']}:\n")
            f.write(f"Role: {char['role']}\n")
            f.write(f"Description: {char['description']}\n")
            f.write(f"Key Traits: {', '.join(char['key_traits'])}\n")
            f.write("\n")
        for chapter_num in range(1, num_chapters + 1):
            chapter_key = f"Chapter_{chapter_num}"
            if "Chapter" not in novel[chapter_key]["final_version"]:
                f.write(f"\nChapter {chapter_num}\n")
            f.write("=" * 50 + "\n\n")
            f.write(novel[chapter_key]["final_version"])
            f.write("\n\n")

if __name__ == "__main__":
    main()
