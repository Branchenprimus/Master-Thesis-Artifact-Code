import argparse
import json
import logging
from openai import OpenAI
from pathlib import Path
from typing import Optional
from pydantic_model import ShexerConfig
import sys

def load_prompt(path: Path) -> str:
    try:
        return path.read_text()
    except Exception as e:
        logging.error(f"Error loading prompt {path}: {str(e)}")
        raise

def generate_shex_params(
    model: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str
) -> Optional[ShexerConfig]:
    client = OpenAI(api_key=api_key)
    
    try:
        # Explicit JSON instruction in user message
        json_user_prompt = f"{user_prompt}\n\nReturn the answer as JSON only."
        
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json_user_prompt}  # Modified line
            ]
        )
        json_str = response.choices[0].message.content
        config_dict = json.loads(json_str)
        return ShexerConfig(**config_dict)
    except Exception as e:
        logging.error(f"OpenAI API error: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--openai_api_key", required=True)
    parser.add_argument("--user_prompt_path", type=Path, required=True)
    parser.add_argument("--system_prompt_path", type=Path, required=True)
    parser.add_argument("--shexer_params_path", type=Path, required=True)
    
    args = parser.parse_args()
    
    try:
        system_prompt = load_prompt(args.system_prompt_path)
        user_prompt = load_prompt(args.user_prompt_path)
        
        config = generate_shex_params(
            model=args.model,
            api_key=args.openai_api_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        if config:
            with args.shexer_params_path.open('w') as f:
                f.write(config.model_dump_json() + '\n')  # ND-JSON format
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"Pipeline failed: {str(e)}")
        sys.exit(2)

if __name__ == "__main__":
    main()