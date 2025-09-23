#!/usr/bin/env python3
"""
YouTube Video Downloader
A simple script to download YouTube videos using yt-dlp
"""

import subprocess
import sys
import os


def check_dependencies():
    """Check if yt-dlp is installed, install if not found"""
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        print("✓ yt-dlp is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("yt-dlp not found. Installing...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'], check=True)
            print("✓ yt-dlp installed successfully")
        except subprocess.CalledProcessError:
            print("✗ Failed to install yt-dlp. Please install manually: pip install yt-dlp")
            return False
    return True


def get_video_url():
    """Get YouTube URL from user input"""
    print("\n" + "="*50)
    print("YouTube Video Downloader")
    print("="*50)
    url = input("Enter YouTube URL: ").strip()

    if not url:
        print("✗ No URL provided")
        return None

    # Basic URL validation
    if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
        print("✗ Please enter a valid YouTube URL")
        return None

    return url


def download_video(url):
    """Download video using yt-dlp"""
    print(f"\n📥 Downloading video from: {url}")

    # Create downloads directory if it doesn't exist
    download_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_dir, exist_ok=True)

    try:
        # Download the best quality video
        result = subprocess.run([
            'yt-dlp',
            '-o', f'{download_dir}/%(title)s.%(ext)s',
            '--progress',
            '--no-playlist',  # Don't download playlists
            url
        ], check=True)

        print("✓ Download completed!")
        print(f"📁 Files saved to: {download_dir}")

    except subprocess.CalledProcessError as e:
        print(f"✗ Download failed: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⚠ Download interrupted by user")
        return False

    return True


def main():
    """Main function"""
    print("YouTube Video Downloader Script")
    print("This script will download YouTube videos using yt-dlp")

    # Check dependencies
    if not check_dependencies():
        return

    # Get URL from user
    url = get_video_url()
    if not url:
        return

    # Download the video
    success = download_video(url)

    if success:
        print("\n🎉 Download completed successfully!")
    else:
        print("\n💥 Download failed. Please try again with a different URL.")


if __name__ == "__main__":
    main()
