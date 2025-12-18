
import google.generativeai as genai
import os

class GeminiClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("API key for Gemini not provided. Please set the GEMINI_API_KEY environment variable.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro-vision')

    def compare_images(self, image_bytes_1, image_bytes_2, prompt):
        if not image_bytes_1 or not image_bytes_2:
            return "No image data provided."

        try:
            image_parts = [
                {
                    "mime_type": "image/jpeg",
                    "data": image_bytes_1
                },
                {
                    "mime_type": "image/jpeg",
                    "data": image_bytes_2
                }
            ]
            prompt_parts = [
                prompt,
                image_parts[0],
                image_parts[1]
            ]
            response = self.model.generate_content(prompt_parts)
            return response.text
        except Exception as e:
            return f"An error occurred: {e}"

    def describe_image(self, image_bytes):
        """
        Describes the given image using the Gemini API.
        
        Args:
            image_bytes: The image data in bytes.
            
        Returns:
            A string containing the description of the image.
        """
        if not image_bytes:
            return "No image data provided."

        try:
            image_parts = [
                {
                    "mime_type": "image/jpeg",
                    "data": image_bytes
                }
            ]
            prompt_parts = [
                "Describe this image in detail:",
                image_parts[0]
            ]
            response = self.model.generate_content(prompt_parts)
            return response.text
        except Exception as e:
            return f"An error occurred: {e}"

