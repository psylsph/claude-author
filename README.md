# Novel Generation Application

This application generates novels using various language models. The application is designed to be easy to use and extendable.

## Installation

To install the application, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/novel-generation-app.git
   ```

2. Navigate to the project directory:
   ```bash
   cd novel-generation-app
   ```

3. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

4. Activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

5. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

To generate a novel, run the following command:
```bash
python app.py
```

The application will prompt you to enter the desired length of the novel and the language model to use. Once you provide the inputs, the application will generate the novel and save it to the `novel_output` directory.

## Application Functionality

The application supports the following language models:
- mistral-nemo-instruct-2407
- writing_partner_mistral_7b - Poor fails to count words even with 32k
- mistral-7b-instruct-v0.3
- mn-violet-lotus-12b - works well
- chronos-gold-12b-1.0 - works well

The application also includes a script to extract the final novel from the generated output:
```bash
python final_novel_extractor.py
```

To publish the generated novel to a PDF file, use the following command:
```bash
python publish_to_pdf.py
```

## Best Language Model

The best language model to use for generating novels is `mistral-nemo-instruct-2407`. This model has been tested and found to perform well with 12k tokens.