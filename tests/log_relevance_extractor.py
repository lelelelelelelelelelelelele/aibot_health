import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging


@dataclass
class RelevanceScoreEntry:
    """Data class to represent a relevance score entry extracted from logs"""
    document_content: str
    metadata: Dict[str, str]
    similarity_score: float
    quality_score: Optional[float]
    source_line: str
    timestamp: Optional[str] = None
    source_file: Optional[str] = None


class LogRelevanceExtractor:
    """
    Auto handling module to extract relevance scores from AI chatbot logs.
    
    This module parses logs from the AI health clinic chatbot and extracts
    relevance scores from vector store warnings, particularly those related
    to document similarity scoring issues in langchain_core/vectorstores.py
    """
    
    def __init__(self):
        # Initialize regex patterns for different parts of the log
        self._setup_patterns()
        # Set up logging
        self.logger = logging.getLogger(__name__)
    
    def _setup_patterns(self):
        """Set up regex patterns for parsing different log elements"""
        # Pattern to match the relevance score warning message
        self.relevance_warning_start_pattern = re.compile(
            r"Relevance scores must be between 0 and 1, got \["
        )
        
        # Pattern to extract source file from metadata
        self.source_file_pattern = re.compile(r"'source':\s*'([^']+)'")
        
        # Pattern to extract quality scores from document content
        self.quality_score_pattern = re.compile(r"'quality_score':\s*([0-9.]+)")
        
        # Pattern to match threshold warnings
        self.threshold_warning_pattern = re.compile(
            r"No relevant docs were retrieved using the relevance score threshold ([0-9.]+)"
        )
        
        # Pattern to match timestamp at the beginning of log lines
        self.timestamp_pattern = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})")
        
    def parse_log_content(self, log_content: str) -> List[RelevanceScoreEntry]:
        """
        Parse the entire log content and extract relevance score entries.
        
        Args:
            log_content: The full content of the log file as a string
            
        Returns:
            A list of RelevanceScoreEntry objects containing the extracted data
        """
        entries = []
        
        # Split log content into individual lines for processing
        lines = log_content.split('\n')
        
        # Process each line to find relevance score warnings
        for line_num, line in enumerate(lines, 1):
            if "Relevance scores must be between 0 and 1" in line:
                try:
                    entries.extend(self._extract_relevance_scores_from_line(line, line_num))
                except Exception as e:
                    self.logger.warning(f"Failed to parse line {line_num}: {e}")
                    continue
        
        return entries
    
    def _extract_relevance_scores_from_line(self, line: str, line_num: int) -> List[RelevanceScoreEntry]:
        """Extract relevance scores from a single log line"""
        entries = []
        
        # Find the start of the relevance warning to extract the document list
        start_match = self.relevance_warning_start_pattern.search(line)
        if not start_match:
            return entries
        
        # Use the improved bracket detection that accounts for brackets inside strings
        start_pos = start_match.end() - 1  # Position of the opening [
        bracket_count = 1
        pos = start_pos + 1  # Start after the opening [
        
        # Track whether we're inside a string literal to ignore brackets inside content
        in_string = False
        string_quote = None
        
        while pos < len(line) and bracket_count > 0:
            char = line[pos]
            
            # Handle string quotes to avoid counting brackets inside strings
            if char in ['"', "'"] and (pos == 0 or line[pos-1] != '\\'):
                if in_string and char == string_quote:
                    in_string = False
                    string_quote = None
                elif not in_string:
                    in_string = True
                    string_quote = char
            elif not in_string:
                # Only count brackets if we're not inside a string
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
            
            pos += 1
        
        if bracket_count != 0:
            self.logger.warning(f"Could not find balanced brackets in line {line_num}")
            return entries
        
        # Extract the document list (including the outer brackets)
        doc_list_str = line[start_pos:pos]  # Include the final ']'
        
        # Process the document list from the extracted string
        doc_matches = self._parse_document_list(doc_list_str)
        
        # For debugging: print how many were found
        self.logger.info(f"Line {line_num}: Found {len(doc_matches)} document matches")
        
        for doc_content, metadata_str, score_str in doc_matches:
            try:
                # Parse the score
                score = float(score_str)
                
                # Extract metadata from string
                metadata = self._parse_metadata(metadata_str)
                
                # Extract quality score if present in document content
                quality_scores = self.quality_score_pattern.findall(doc_content)
                quality_score = float(quality_scores[0]) if quality_scores else None
                
                # Extract timestamp from the original line
                timestamp_match = self.timestamp_pattern.search(line)
                timestamp = timestamp_match.group(1) if timestamp_match else None
                
                # Create RelevanceScoreEntry
                entry = RelevanceScoreEntry(
                    document_content=doc_content[:500] + "..." if len(doc_content) > 500 else doc_content,
                    metadata=metadata,
                    similarity_score=score,
                    quality_score=quality_score,
                    source_line=line,
                    timestamp=timestamp,
                    source_file=metadata.get('source')
                )
                
                entries.append(entry)
                
            except ValueError as e:
                self.logger.warning(f"Could not parse score on line {line_num}: {e}")
                continue
            except Exception as e:
                self.logger.warning(f"Error processing document on line {line_num}: {e}")
                continue
        
        return entries
    
    def _parse_document_list(self, doc_list_str: str) -> List[Tuple[str, str, str]]:
        """
        Parse a document list string to extract document content, metadata, and scores.
        
        Args:
            doc_list_str: String containing the document list from the log
            
        Returns:
            List of tuples containing (document_content, metadata_str, score_str)
        """
        results = []
        
        try:
            pos = 0
            iteration = 0
            while pos < len(doc_list_str) and iteration < 20:  # Prevent infinite loops with higher limit
                doc_start = doc_list_str.find("Document(", pos)
                if doc_start == -1:
                    break
                
                # Count parentheses to find the end of the Document part
                paren_count = 1
                doc_end = doc_start + 9  # after "Document("
                
                # Track string literals to avoid counting parentheses inside strings
                in_string = False
                string_quote = None
                
                while doc_end < len(doc_list_str) and paren_count > 0:
                    char = doc_list_str[doc_end]
                    
                    # Handle string quotes to avoid counting parentheses inside strings
                    if char in ['"', "'"] and (doc_end == 0 or doc_list_str[doc_end-1] != '\\'):
                        if in_string and char == string_quote:
                            in_string = False
                            string_quote = None
                        elif not in_string:
                            in_string = True
                            string_quote = char
                    elif not in_string:
                        # Only count parentheses if we're not inside a string
                        if char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                    
                    doc_end += 1
                
                if paren_count != 0:
                    # Could not find end of Document, try to continue from next position
                    pos = doc_start + 1
                    continue
                
                # Extract document part
                doc_part = doc_list_str[doc_start:doc_end]
                
                # Now find the score after this Document
                after_doc = doc_end
                while after_doc < len(doc_list_str) and doc_list_str[after_doc] in [' ', ',', ')']:
                    after_doc += 1
                
                remaining = doc_list_str[after_doc:]
                score_match = re.match(r'([-+]?\d*\.?\d+)', remaining)
                if score_match:
                    score = score_match.group(1)
                    
                    # Try to extract content and metadata
                    # Handle both single and double quotes separately
                    content_match = None
                    quote_type = None
                    
                    # First, try to find single quote pattern
                    single_quote_match = re.search(r"page_content='((?:[^']|\\')*?)'", doc_part, re.DOTALL)
                    if single_quote_match:
                        content_match = single_quote_match
                        quote_type = "'"
                    else:
                        # Try double quote pattern
                        double_quote_match = re.search(r'page_content="((?:[^"]|\\")*?)"', doc_part, re.DOTALL)
                        if double_quote_match:
                            content_match = double_quote_match
                            quote_type = '"'
                    
                    # Find metadata
                    metadata_match = re.search(r"metadata=({[^}]*}[)}]*)", doc_part) or re.search(r"metadata=({.*?}\))", doc_part)
                    
                    if content_match and metadata_match:
                        content = content_match.group(1)
                        metadata = metadata_match.group(1)
                        # Unescape quotes
                        unescaped_content = content.replace("\\'", "'").replace('\\"', '"')
                        results.append((unescaped_content, metadata, score))
                    
                    # Move past this document and score
                    pos = after_doc + len(score_match.group(0))
                else:
                    # No score found, move to next position
                    pos = doc_end
                
                iteration += 1
        
        except re.error as e:
            # For debugging purposes, let's see what the error is
            import traceback
            self.logger.error(f"Regex error while parsing document list: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        except Exception as e:
            import traceback
            self.logger.error(f"Error parsing document list: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        
        return results
    
    def _parse_metadata(self, metadata_str: str) -> Dict[str, str]:
        """
        Parse metadata string into a dictionary.
        
        Args:
            metadata_str: String containing metadata in Python dict format
            
        Returns:
            Dictionary with parsed metadata
        """
        metadata = {}
        
        try:
            # Extract source file
            source_match = self.source_file_pattern.search(metadata_str)
            if source_match:
                metadata['source'] = source_match.group(1)
            
            # Add other metadata as needed
            # This could be expanded to extract other fields like 'id', 'seq_num', etc.
            id_match = re.search(r"'id':\s*'([^']+)'", metadata_str)
            if id_match:
                metadata['id'] = id_match.group(1)
                
            seq_num_match = re.search(r"'seq_num':\s*(\d+)", metadata_str)
            if seq_num_match:
                metadata['seq_num'] = seq_num_match.group(1)
        except re.error as e:
            self.logger.error(f"Regex error while parsing metadata: {e}")
        except Exception as e:
            self.logger.error(f"Error parsing metadata: {e}")
        
        return metadata
    
    def extract_threshold_warnings(self, log_content: str) -> List[Dict]:
        """
        Extract threshold warnings from the log content.
        
        Args:
            log_content: The full content of the log file as a string
            
        Returns:
            A list of dictionaries containing threshold warning information
        """
        warnings = []
        
        # Find threshold warning lines
        for line_num, line in enumerate(log_content.split('\n'), 1):
            if "No relevant docs were retrieved using the relevance score threshold" in line:
                try:
                    threshold_matches = self.threshold_warning_pattern.findall(line)
                    
                    for threshold in threshold_matches:
                        warnings.append({
                            'line_number': line_num,
                            'threshold': float(threshold),
                            'source_line': line
                        })
                except ValueError as e:
                    self.logger.warning(f"Could not parse threshold value on line {line_num}: {e}")
                    continue
                except Exception as e:
                    self.logger.error(f"Error processing threshold warning on line {line_num}: {e}")
                    continue
        
        return warnings
    
    def handle_malformed_entries(self, log_content: str) -> List[Dict]:
        """
        Identify and report malformed log entries that couldn't be parsed normally.
        
        Args:
            log_content: The full content of the log file as a string
            
        Returns:
            A list of dictionaries containing information about malformed entries
        """
        malformed_entries = []
        
        for line_num, line in enumerate(log_content.split('\n'), 1):
            # Look for lines that seem to contain relevance information but don't match our patterns
            if ("Relevance scores must be between 0 and 1" in line or 
                "No relevant docs were retrieved" in line or
                "Document(" in line):
                
                # Check if this line has already been successfully parsed
                is_parsed = False
                
                # Check for relevance warnings
                if "Relevance scores must be between 0 and 1" in line:
                    relevance_start_match = self.relevance_warning_start_pattern.search(line)
                    if relevance_start_match:
                        # Use the same improved bracket detection as in the main method
                        start_pos = relevance_start_match.end() - 1  # Position of the opening [
                        bracket_count = 1
                        pos = start_pos + 1  # Start after the opening [
                        
                        # Track whether we're inside a string literal to ignore brackets inside content
                        in_string = False
                        string_quote = None
                        
                        while pos < len(line) and bracket_count > 0:
                            char = line[pos]
                            
                            # Handle string quotes to avoid counting brackets inside strings
                            if char in ['"', "'"] and (pos == 0 or line[pos-1] != '\\'):
                                if in_string and char == string_quote:
                                    in_string = False
                                    string_quote = None
                                elif not in_string:
                                    in_string = True
                                    string_quote = char
                            elif not in_string:
                                # Only count brackets if we're not inside a string
                                if char == '[':
                                    bracket_count += 1
                                elif char == ']':
                                    bracket_count -= 1
                            
                            pos += 1
                        
                        if bracket_count == 0:
                            # Extract the document list (including the outer brackets)
                            doc_list_str = line[start_pos:pos]  # Include the final ']'
                            # Process the document list from the extracted string
                            doc_matches = self._parse_document_list(doc_list_str)
                            if doc_matches:  # If we could parse documents, it's not malformed
                                is_parsed = True
                        if not is_parsed:
                            malformed_entries.append({
                                'line_number': line_num,
                                'type': 'relevance_warning_no_docs',
                                'issue': 'Found relevance warning but could not parse document list',
                                'source_line': line
                            })
                
                # Check for threshold warnings
                elif "No relevant docs were retrieved" in line:
                    threshold_matches = self.threshold_warning_pattern.findall(line)
                    if not threshold_matches:
                        malformed_entries.append({
                            'line_number': line_num,
                            'type': 'threshold_warning_malformed',
                            'issue': 'Found threshold warning but could not parse threshold value',
                            'source_line': line
                        })
        
        return malformed_entries
    
    def format_as_json(self, entries: List[RelevanceScoreEntry]) -> str:
        """
        Format the extracted relevance scores as JSON.
        
        Args:
            entries: List of RelevanceScoreEntry objects
            
        Returns:
            JSON formatted string
        """
        import json
        
        formatted_entries = []
        for entry in entries:
            formatted_entries.append({
                'document_content': entry.document_content,
                'metadata': entry.metadata,
                'similarity_score': entry.similarity_score,
                'quality_score': entry.quality_score,
                'timestamp': entry.timestamp,
                'source_file': entry.source_file,
                'source_line': entry.source_line  # Only include first 200 chars to avoid large output
            })
        
        return json.dumps(formatted_entries, indent=2, ensure_ascii=False)
    
    def format_as_csv(self, entries: List[RelevanceScoreEntry]) -> str:
        """
        Format the extracted relevance scores as CSV.
        
        Args:
            entries: List of RelevanceScoreEntry objects
            
        Returns:
            CSV formatted string
        """
        import io
        import csv
        
        if not entries:
            return ""
        
        output = io.StringIO()
        fieldnames = ['document_content', 'source_file', 'similarity_score', 'quality_score', 'timestamp']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        writer.writeheader()
        for entry in entries:
            writer.writerow({
                'document_content': entry.document_content.replace('\n', ' ').replace('\r', ''),
                'source_file': entry.source_file,
                'similarity_score': entry.similarity_score,
                'quality_score': entry.quality_score,
                'timestamp': entry.timestamp
            })
        
        return output.getvalue()
    
    def generate_summary_report(self, entries: List[RelevanceScoreEntry]) -> str:
        """
        Generate a summary report of the extracted relevance scores.
        
        Args:
            entries: List of RelevanceScoreEntry objects
            
        Returns:
            Summary report as a formatted string
        """
        if not entries:
            return "No relevance score entries found in the log."
        
        # Calculate statistics
        scores = [entry.similarity_score for entry in entries]
        quality_scores = [entry.quality_score for entry in entries if entry.quality_score is not None]
        
        avg_similarity = sum(scores) / len(scores) if scores else 0
        min_similarity = min(scores) if scores else 0
        max_similarity = max(scores) if scores else 0
        
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0 if quality_scores else "N/A"
        min_quality = min(quality_scores) if quality_scores else "N/A"
        max_quality = max(quality_scores) if quality_scores else "N/A"
        
        # Count by source file
        source_counts = {}
        for entry in entries:
            source = entry.source_file or "Unknown"
            source_counts[source] = source_counts.get(source, 0) + 1
        
        report = f"""
Relevance Score Analysis Report
===============================

Total entries found: {len(entries)}
Average similarity score: {avg_similarity:.4f}
Min similarity score: {min_similarity:.4f}
Max similarity score: {max_similarity:.4f}

Quality scores (when available):
Average quality score: {avg_quality if avg_quality != "N/A" else "N/A"}
Min quality score: {min_quality if min_quality != "N/A" else "N/A"}
Max quality score: {max_quality if max_quality != "N/A" else "N/A"}

Entries by source file:
"""
        for source, count in source_counts.items():
            report += f"- {source}: {count} entries\n"
        
        report += "\nDetailed entries:\n"
        report += "-" * 80 + "\n"
        
        for i, entry in enumerate(entries, 1):
            report += f"{i}. Source: {entry.source_file or 'Unknown'}\n"
            report += f"   Similarity Score: {entry.similarity_score}\n"
            report += f"   Quality Score: {entry.quality_score or 'N/A'}\n"
            report += f"   Content Preview: {entry.document_content[:100]}...\n"
            report += f"   Timestamp: {entry.timestamp or 'N/A'}\n"
            report += "\n"
        
        return report
    
    def save_results(self, entries: List[RelevanceScoreEntry], output_format: str = "json", 
                     output_file: str = None) -> str:
        """
        Save the results in the specified format.
        
        Args:
            entries: List of RelevanceScoreEntry objects
            output_format: Format to save in ('json', 'csv', 'report')
            output_file: Optional file path to save to
            
        Returns:
            Formatted results as string
        """
        if output_format.lower() == "json":
            result = self.format_as_json(entries)
        elif output_format.lower() == "csv":
            result = self.format_as_csv(entries)
        elif output_format.lower() == "report":
            result = self.generate_summary_report(entries)
        else:
            raise ValueError(f"Unsupported format: {output_format}. Use 'json', 'csv', or 'report'.")
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
        
        return result
    
    def process_log_file(self, file_path: str) -> List[RelevanceScoreEntry]:
        """
        Process a single log file and extract relevance scores.
        
        Args:
            file_path: Path to the log file
            
        Returns:
            List of RelevanceScoreEntry objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
            return self.parse_log_content(log_content)
        except FileNotFoundError:
            self.logger.error(f"Log file not found: {file_path}")
            return []
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    log_content = f.read()
                return self.parse_log_content(log_content)
            except UnicodeDecodeError:
                self.logger.error(f"Could not decode log file: {file_path}")
                return []
        except Exception as e:
            self.logger.error(f"Error processing log file {file_path}: {e}")
            return []
    
    def process_multiple_log_files(self, file_paths: List[str]) -> List[RelevanceScoreEntry]:
        """
        Process multiple log files and combine the results.
        
        Args:
            file_paths: List of paths to log files
            
        Returns:
            Combined list of RelevanceScoreEntry objects from all files
        """
        all_entries = []
        
        for file_path in file_paths:
            self.logger.info(f"Processing log file: {file_path}")
            entries = self.process_log_file(file_path)
            all_entries.extend(entries)
        
        return all_entries
    
    def process_log_directory(self, directory_path: str, file_pattern: str = "*.log") -> List[RelevanceScoreEntry]:
        """
        Process all log files in a directory that match the given pattern.
        
        Args:
            directory_path: Path to the directory containing log files
            file_pattern: Pattern to match log files (default: "*.log")
            
        Returns:
            Combined list of RelevanceScoreEntry objects from all matching files
        """
        import glob
        import os
        
        # Find all matching files in the directory
        search_pattern = os.path.join(directory_path, file_pattern)
        file_paths = glob.glob(search_pattern)
        
        # Also look for .txt and other common log extensions
        if file_pattern == "*.log":
            for ext in [".txt", ".out", ".log"]:
                search_pattern = os.path.join(directory_path, f"*{ext}")
                file_paths.extend(glob.glob(search_pattern))
        
        # Remove duplicates
        file_paths = list(set(file_paths))
        
        self.logger.info(f"Found {len(file_paths)} files matching pattern in {directory_path}")
        return self.process_multiple_log_files(file_paths)


if __name__ == "__main__":
    # Quick demo functionality moved from test_log_extractor.py
    import sys
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Sample log data for immediate testing
    example_log = r'''H:\project\aibot\.venv\lib\site-packages\langchain_core\vectorstores.py:330: UserWarning: Relevance scores must be between 0 and 1, got [(Document(page_content='Sample content', metadata={'source': 'test.json'}), 0.025)]'''
    
    extractor = LogRelevanceExtractor()
    if len(sys.argv) > 1:
        # If file path provided, process it
        entries = extractor.process_log_file(sys.argv[1])
    else:
        # Otherwise run on sample
        print("No log file provided. Running on sample data...")
        entries = extractor.parse_log_content(example_log)
    
    print(extractor.generate_summary_report(entries))