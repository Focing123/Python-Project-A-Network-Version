import subprocess
import os
from datetime import datetime

def get_git_commits():
    try:
        # Get git log with format: hash, author, date, and subject
        git_log = subprocess.check_output(
            ['git', 'log', '--pretty=format:%H|%an|%ad|%s', '--date=format:%Y-%m-%d %H:%M:%S'],
            universal_newlines=True
        )
        
        # Create output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f'commit_history_{timestamp}.txt'
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("Git Commit History\n")
            f.write("=================\n\n")
            
            for line in git_log.split('\n'):
                if line:
                    commit_hash, author, date, subject = line.split('|')
                    f.write(f"Commit: {commit_hash[:8]}\n")
                    f.write(f"Author: {author}\n")
                    f.write(f"Date: {date}\n")
                    f.write(f"Subject: {subject}\n")
                    f.write("-" * 50 + "\n\n")
        
        print(f"Commit history has been saved to {output_file}")
        
    except subprocess.CalledProcessError:
        print("Error: Not a git repository or git is not installed")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    get_git_commits()