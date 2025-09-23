#!/usr/bin/env python3
"""
YouTube Playlist Downloader
A script to download entire YouTube playlists using yt-dlp
"""

import subprocess
import sys
import os
import re


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


def get_playlist_url():
    """Get YouTube playlist URL from user input"""
    print("\n" + "="*50)
    print("YouTube Playlist Downloader")
    print("="*50)
    url = input("Enter YouTube Playlist URL: ").strip()

    if not url:
        print("✗ No URL provided")
        return None

    # Basic URL validation for playlist
    if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
        print("✗ Please enter a valid YouTube URL")
        return None

    # Check if it's a playlist URL
    if 'list=' not in url:
        print("✗ Please enter a playlist URL (should contain 'list=' parameter)")
        return None

    return url


def sanitize_folder_name(name):
    """Sanitize playlist name for use as folder name"""
    # Remove or replace invalid characters for folder names
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'[^\w\s-]', '', name)
    name = name.strip()
    return name[:50]  # Limit folder name length


def get_playlist_info(url):
    """Get playlist information without downloading"""
    try:
        result = subprocess.run([
            'yt-dlp',
            '--flat-playlist',
            '--print', '%(playlist_title)s',
            '--print', '%(playlist_count)s',
            url
        ], capture_output=True, text=True, check=True)

        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            playlist_title = lines[0]
            playlist_count = lines[1]

            # Clean up playlist title for folder name
            folder_name = sanitize_folder_name(playlist_title)
            if not folder_name:
                folder_name = f"playlist_{len(lines[1])}"

            return folder_name, int(playlist_count)

    except subprocess.CalledProcessError:
        pass

    return None, 0


def download_playlist(url, folder_name, video_count):
    """Download entire playlist using yt-dlp"""
    print(f"\n📥 Downloading playlist: {folder_name}")
    print(f"🎥 Videos in playlist: {video_count}")

    # Create playlist-specific folder
    download_dir = os.path.join(os.getcwd(), "playlists", folder_name)
    os.makedirs(download_dir, exist_ok=True)

    try:
        # Download the entire playlist with best quality
        result = subprocess.run([
            'yt-dlp',
            '-o', f'{download_dir}/%(playlist_index)s - %(title)s.%(ext)s',
            '--progress',
            '--yes-playlist',  # Download entire playlist
            '--playlist-items', '1-50',  # Limit to first 50 videos (adjust as needed)
            url
        ], check=True)

        print("✓ Playlist download completed!")
        print(f"📁 All videos saved to: {download_dir}")

    except subprocess.CalledProcessError as e:
        print(f"✗ Download failed: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⚠ Download interrupted by user")
        return False

    return True


def main():
    """Main function"""
    print("YouTube Playlist Downloader Script")
    print("This script will download entire YouTube playlists using yt-dlp")

    # Check dependencies
    if not check_dependencies():
        return

    # Get playlist URL from user
    url = get_playlist_url()
    if not url:
        return

    # Get playlist information
    print("📊 Analyzing playlist...")
    folder_name, video_count = get_playlist_info(url)

    if not folder_name:
        print("✗ Could not retrieve playlist information")
        return

    print(f"📋 Playlist name: {folder_name}")
    print(f"🎥 Number of videos: {video_count}")

    # Confirm download
    response = input(f"\n🔄 Download {video_count} videos? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Download cancelled")
        return

    # Download the playlist
    success = download_playlist(url, folder_name, video_count)

    if success:
        print("\n🎉 Playlist download completed successfully!")
        print("💡 Tip: Videos are organized by playlist index number")
    else:
        print("\n💥 Playlist download failed. Please try again.")


if __name__ == "__main__":
    main()
