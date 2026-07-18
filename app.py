import streamlit as st
import os
import subprocess
import json
import math
import concurrent.futures
from openai import OpenAI
from pathlib import Path

# Initialize OpenAI client
client = OpenAI()

st.set_page_config(page_title="Video & Text Processor", layout="wide")

def count_paragraphs(text):
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    return paragraphs

def get_video_duration(video_path):
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)

def split_video(video_path, output_dir, num_segments):
    duration = get_video_duration(video_path)
    segment_duration = duration / num_segments
    
    segments = []
    for i in range(num_segments):
        start_time = i * segment_duration
        output_path = os.path.join(output_dir, f"segment_{i}.mp4")
        cmd = [
            'ffmpeg', '-y', '-ss', str(start_time), '-t', str(segment_duration),
            '-i', video_path, '-c', 'copy', output_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        segments.append(output_path)
    return segments, segment_duration

def generate_tts(text, output_path):
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text
    )
    response.stream_to_file(output_path)
    return output_path

def get_audio_duration(audio_path):
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout)

def process_segment(index, text, video_segment, audio_dir, final_segments_dir):
    # 1. Generate TTS
    audio_path = os.path.join(audio_dir, f"audio_{index}.mp3")
    generate_tts(text, audio_path)
    
    audio_duration = get_audio_duration(audio_path)
    
    # 2. Apply "3s play, 2s freeze" and adjust speed to match audio duration
    # This is a complex ffmpeg filter. 
    # For simplicity in this script, we'll first create the "freeze" effect and then scale it.
    # Effect: play 3s, freeze 2s. Total cycle 5s. 
    # If we want it to match audio_duration, we need to adjust the speed.
    
    output_segment = os.path.join(final_segments_dir, f"final_segment_{index}.mp4")
    
    # First, let's get the original segment duration
    orig_segment_duration = get_video_duration(video_segment)
    
    # The user asked for "3 seconds play 2 seconds Freeze".
    # This means a 5s cycle where 3s is moving and 2s is frozen.
    # We will implement this using a complex filter.
    
    # We need to scale the video to match audio duration first, then apply the freeze effect,
    # OR apply freeze effect and then scale. Let's scale first.
    
    speed_factor = audio_duration / orig_segment_duration
    
    # Filter for 3s play, 2s freeze:
    # mod(t, 5) < 3 -> normal play
    # mod(t, 5) >= 3 -> freeze at the 3s mark of each 5s block
    # We use 'eval' with 'if' in 'setpts' to achieve the freeze.
    # However, a simpler way is using 'sendcmd' or multiple filters.
    # Let's use: if(mod(t,5)<3, t, floor(t/5)*5+3)
    
    freeze_filter = (
        f"setpts='if(lt(mod(t,5),3), t, floor(t/5)*5+3)/TB',"
        f"setpts={speed_factor}*PTS"
    )
    
    cmd = [
        'ffmpeg', '-y', '-i', video_segment, '-i', audio_path,
        '-filter_complex', f"[0:v]{freeze_filter}[v]",
        '-map', '[v]', '-map', '1:a', '-shortest', output_segment
    ]
    
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_segment

def main():
    st.title("🎬 AI Video & Text Processor")
    st.markdown("""
    This app splits a video into segments based on the number of paragraphs in your text, 
    generates TTS for each paragraph, adjusts video speed to match the audio, 
    and applies a '3s Play, 2s Freeze' effect for copyright protection.
    """)

    with st.sidebar:
        st.header("Inputs")
        text_input = st.text_area("Enter Text (Unlimited words)", height=300)
        video_file = st.file_uploader("Upload Video (Max 2GB, 1 Hour)", type=["mp4", "mov", "avi"])

    if st.button("Start Processing"):
        if not text_input or not video_file:
            st.error("Please provide both text and a video file.")
            return

        paragraphs = count_paragraphs(text_input)
        num_paragraphs = len(paragraphs)
        st.info(f"Detected {num_paragraphs} paragraphs.")

        # Save uploaded video
        os.makedirs("temp", exist_ok=True)
        video_path = os.path.join("temp", video_file.name)
        with open(video_path, "wb") as f:
            f.write(video_file.getbuffer())

        # Create directories
        audio_dir = "temp/audio"
        segments_dir = "temp/segments"
        final_segments_dir = "temp/final_segments"
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(segments_dir, exist_ok=True)
        os.makedirs(final_segments_dir, exist_ok=True)

        # 1. Split Video
        with st.status("Splitting video into segments...") as status:
            video_segments, seg_dur = split_video(video_path, segments_dir, num_paragraphs)
            status.update(label="Video split complete!", state="complete")

        # 2. Process segments in parallel
        st.write("Processing segments (TTS + Speed Adjustment + Effects)...")
        progress_bar = st.progress(0)
        
        final_video_segments = [None] * num_paragraphs
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_index = {
                executor.submit(process_segment, i, paragraphs[i], video_segments[i], audio_dir, final_segments_dir): i 
                for i in range(num_paragraphs)
            }
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result_path = future.result()
                    final_video_segments[index] = result_path
                except Exception as e:
                    st.error(f"Error processing segment {index}: {e}")
                
                completed += 1
                progress_bar.progress(completed / num_paragraphs)

        # 3. Merge final segments
        st.write("Merging all segments into final video...")
        list_file = "temp/concat_list.txt"
        with open(list_file, "w") as f:
            for seg in final_video_segments:
                if seg:
                    f.write(f"file '{os.path.abspath(seg)}'\n")

        final_output = "output_final.mp4"
        merge_cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_file,
            '-c', 'copy', final_output
        ]
        subprocess.run(merge_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        st.success("Processing complete!")
        st.video(final_output)
        
        with open(final_output, "rb") as f:
            st.download_button("Download Final Video", f, file_name="processed_video.mp4")

if __name__ == "__main__":
    main()
