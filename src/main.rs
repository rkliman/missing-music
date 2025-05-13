use reqwest::blocking::Client;
use reqwest::header::PROXY_AUTHORIZATION;
use serde::Deserialize;
use urlencoding::encode;
use std::fs;
use std::path::Path;
use std::process::Command;

#[derive(Debug, Deserialize)]
struct ReleaseSearchResult {
    releases: Vec<Release>,
}

#[derive(Debug, Deserialize, Clone)]
struct Release {
    title: String,
    id: String,
    #[serde(rename = "date")]
    release_date: Option<String>,
}

#[derive(Debug, Deserialize)]
struct DetailedRelease {
    media: Vec<Media>,  // media contains the tracks
}

#[derive(Debug, Deserialize)]
struct Media {
    tracks: Option<Vec<Track>>,  // tracks are inside media
}

#[derive(Debug, Deserialize, Clone)]
struct Track {
    title: String,
}

fn pick_earliest_official_release(releases: &[Release]) -> Option<Release> {
    let mut known_date_releases: Vec<Release> = releases
        .iter()
        .filter(|r| r.release_date.is_some())
        .cloned()
        .collect();

    if known_date_releases.is_empty() {
        known_date_releases = releases.to_vec();
    }

    known_date_releases.sort_by_key(|r| r.release_date.clone().unwrap_or_default());
    known_date_releases.first().cloned()
}

fn get_tracks_for_release(client: &Client, release_id: &str) -> Result<Option<Vec<Track>>, Box<dyn std::error::Error>> {
    let url = format!(
        "https://musicbrainz.org/ws/2/release/{}?inc=recordings&fmt=json",
        release_id
    );

    let res = client.get(&url)
        .header("User-Agent", "missing-music/0.1.0 ( randall@example.com )")
        .send()?;

    let detailed_release: DetailedRelease = res.json()?;

    // Extract tracks from the first media entry (if it exists)
    if let Some(media) = detailed_release.media.get(0) {
        Ok(media.tracks.clone())  // Return tracks if present
    } else {
        Ok(None)  // No media or tracks available
    }
}

fn get_tracks_by_album(client: &Client, album: &str, artist: &str) -> Result<Vec<Track>, Box<dyn std::error::Error>> {
    let query = format!("release:\"{}\" AND artist:\"{}\" AND primarytype:album AND status:official", album, artist);
    let url = format!(
        "https://musicbrainz.org/ws/2/release/?query={}&fmt=json",
        encode(&query)
    );
    let res = client.get(&url)
        .header("User-Agent", "missing-music/0.1.0 ( randall@example.com )")
        .send()?;
    let search_result: ReleaseSearchResult = res.json()?;


    if let Some(earliest_release) = pick_earliest_official_release(&search_result.releases) {
        println!("Earliest official release: {}", earliest_release.title);
        
        // Fetch and display tracks for the earliest release
        match get_tracks_for_release(&client, &earliest_release.id)? {
            Some(tracks) => {
                println!("Tracks in '{}' release:", earliest_release.title);
                for track in tracks {
                    println!("- {}", track.title);
                }
            }
            None => println!("No tracks available for this release."),
        }
    } else {
        println!("No official releases found.");
    }
}


fn main() -> Result<(), Box<dyn std::error::Error>> {
    // let client = Client::new();

    // let music_folders: Vec<_> = match fs::read_dir("/home/randall/Music") {
    //     Err(why) => {
    //         println!("! {:?}", why.kind());
    //         Vec::new()
    //     }
    //     Ok(paths) => paths.filter_map(|entry| {
    //         if let Ok(entry) = entry {
    //             let path = entry.path();
    //             if path.is_dir() {
    //                 return Some(path);
    //             }
    //         }
    //         None
    //     }).collect(),
    // };

    // for folder in &music_folders {
    //     let songs: Vec<_> = match fs::read_dir(folder) {
    //         Err(why) => {
    //             println!("! {:?}", why.kind());
    //             Vec::new()
    //         }
    //         Ok(paths) => paths.filter_map(|entry| {
    //             if let Ok(entry) = entry {
    //                 let path = entry.path();
    //                 if path.is_file() {
    //                     return path.file_stem().map(|stem| stem.to_string_lossy().to_string());
    //                 }
    //             }
    //             None
    //         }).collect(),
    //     };
    //     // println!("Songs in folder: {:?}", songs);
    //     // get artist and album from the folder name
    //     let folder_name = folder.file_name().unwrap_or_default().to_string_lossy().to_string();
        
    //     let parts: Vec<&str> = songs[0].split(" - ").collect();
    //     if parts.len() < 2 {
    //         println!("! Invalid folder name format: {}", folder_name);
    //         continue;
    //     }
    //     let artist = parts[0].trim();
    //     println!("Album: {}, Artist: {}", folder_name, artist);
    //     let song_names: Vec<&str> = songs.iter()
    //         .filter_map(|s| s.split(" - ").nth(1))  // Get the second element if it exists
    //         .collect();

    //     println!("Songs: {:?}", song_names);
    // }
    
    
    Ok(())
}
