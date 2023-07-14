#!/bin/python3

"""
Simple Plymouth theme generator.
"""

import os
import sys
import json
import getopt
import ffmpeg


def prepare_build_directory(path):
    """
    Prepare the build directory.
    Check if exists and create it if needed.
    Stop the program if there is a blocking issue.

    Parameters
    ----------
    path : str
        Path (may be relative) to the build directory.
    """
    if os.path.exists(path):
        # Check if it's a directory.
        if os.path.isfile(path):
            print(f"The specified build path '{path}' is a file")
            sys.exit(-1)
        print(f"Using existing output directory '{path}'")
    else:
        os.makedirs(path)
        print(f"Created output directory '{path}'")


def check_file_exists(path):
    """
    Check if a file exists at the specified path.

    Parameters
    ----------
    path : str
        Path to the file to check.
    """
    if not (os.path.exists(path) and os.path.isfile(path)):
        print(f"The file '{path}' doesn't exists or is not a valid file")
        sys.exit(-1)
    else:
        print(f"File '{path}' available")


def check_input_assets(configuration):
    """
    Check if the input assets are present.

    Parameters
    ----------
    configuration : dict
        Overall configuration.
    """
    source_dir = configuration["source"]
    if (not os.path.exists(source_dir)) or os.path.isfile(source_dir):
        print(f"Invalid assets directory '{source_dir}'")
        sys.exit(-1)
    check_file_exists(f"{source_dir}/{configuration['animation']}")
    dialog = configuration["dialog"]
    check_file_exists(f"{source_dir}/{dialog['box']}")
    check_file_exists(f"{source_dir}/{dialog['entry']}")
    check_file_exists(f"{source_dir}/{dialog['bullet']}")
    check_file_exists(f"{source_dir}/{dialog['lock']}")
    progression = configuration["progression"]
    check_file_exists(f"{source_dir}/{progression['box']}")
    check_file_exists(f"{source_dir}/{progression['bar']}")


def extract_frames_from_video(video_path, output_path, fps):
    """
    Extract frames from the input video and copy them into the output directory.

    Parameters
    ----------
    video_path : str
        Path to the input video.
    output_path : str
        Path to the output directory.
    fps : int
        Frame per second

    Returns
    -------
    int
        the number of extracted frames
    """
    print(f"Generate animation frames from video '{video_path}'")
    probe = ffmpeg.probe(video_path)
    time = float(probe["streams"][0]["duration"])
    width = probe["streams"][0]["width"]
    height = probe["streams"][0]["height"]
    nb_frames = int(probe["streams"][0]["nb_frames"])
    source_fps = int(nb_frames / time)
    print(f"Input video duration = {time} seconds @ {source_fps} fps")
    print(f"Input video size = {width}x{height}")
    number_of_extracts = int(time) * fps
    print(f"The result should be {number_of_extracts} images")

    ffmpeg.input(video_path).filter("scale", width, -1).filter("fps", fps).output(
        f"{output_path}/animation_frame_%d.png"
    ).run(quiet=True, overwrite_output=True)

    return number_of_extracts


def write_plymouth_file(configuration):
    """
    Write the Plymouth theme file.

    Parameters
    ----------
    configuration : dict
        Configuration.
    """
    theme_name = configuration["name"]
    theme_directory = configuration["theme_directory"]
    theme_filepath = f"{configuration['build']}/{theme_name}.plymouth"
    with open(theme_filepath, "w", encoding="UTF-8") as plymouth_file:
        plymouth_file.write(
            (
                "[Plymouth Theme]\n"
                f"Name={theme_name}\n"
                f"Description={configuration['description']}\n"
                "ModuleName=script\n\n"
                "[script]\n"
                f"ImageDir={theme_directory}/{theme_name}\n"
                f"ScriptFile={theme_directory}/{theme_name}/{theme_name}.script\n"
            )
        )
        plymouth_file.close()
        print(f"Plymouth theme file '{theme_filepath}' created/updated")


def write_plymouth_script(configuration, frame_count):
    """
    Write the Plymouth script file.

    Parameters
    ----------
    configuration : dict
        Configuration
    frame_count : int
        Number of frame files for the animation
    """
    theme_name = configuration["name"]
    theme_directory = configuration["theme_directory"]
    script_filepath = f"{configuration['build']}/{theme_name}.script"
    with open(script_filepath, "w", encoding="UTF-8") as script_file:
        # Load the animation frames.
        script_file.write(
            (
                f"for (i = 0; i < {frame_count}; i++)\n"
                '   animation_image[i] = Image("animation_frame_" + i + ".png");\n'
                "animation_sprite = Sprite();\n\n"
                "animation_sprite.SetX(Window.GetWidth() / 2 - animation_image[0].GetWidth() / 2);\n"
                "animation_sprite.SetY(Window.GetHeight() / 2 - animation_image[0].GetHeight() / 2);\n"
            )
        )
        script_file.close()
        print(f"Plymouth script file '{script_filepath}' created/updated")


def build_theme(configuration):
    """
    Build the custom theme.

    Parameters
    ----------
    configuration : dict
        The configuration dictionnary containing all the needed information
        to retrieve input assets and delivering the packaged custom theme.
    """
    check_input_assets(configuration)
    prepare_build_directory(configuration["build"])
    # At this point, we are sure that every inputs and outputs are correct.
    write_plymouth_file(configuration)
    number_of_extracts = extract_frames_from_video(
        f"{configuration['source']}/{configuration['animation']}",
        configuration["build"],
        configuration["fps"],
    )
    write_plymouth_script(configuration, number_of_extracts)


def main():
    """
    Main function and entry point.
    """

    custom_configuration_file = False
    configuration_filepath = "config.json"
    configuration = {
        "name": "custom",
        "description": "A custom theme for Plymouth",
        "theme_directory": "/usr/share/plymouth/themes",
        "source": "./source",
        "build": "./build",
        "animation": "animation.mp4",
        "fps": 25,
        "dialog": {
            "box": "box.png",
            "entry": "entry.png",
            "bullet": "bullet.png",
            "lock": "lock.png",
            "ratio": 0.6,
        },
        "progression": {
            "bar": "progress_bar.png",
            "box": "progress_box.png",
            "ratio": 0.6,
        },
    }

    try:
        opts, _args = getopt.getopt(sys.argv[1:], "c:")
    except getopt.GetoptError:
        print(f"{sys.argv[0]} -c [path_to_configfile]")
        sys.exit(1)

    for opt, arg in opts:
        if opt == "-c":
            custom_configuration_file = True
            configuration_filepath = arg

    try:
        with open(configuration_filepath, "r", encoding="UTF-8") as configuration_file:
            custom_configuration = json.load(configuration_file)
            configuration_file.close()
            configuration.update(custom_configuration)
    except FileNotFoundError:
        if custom_configuration_file:
            print(
                f"The provided configuration file '{configuration_filepath}' doesn't exist."
            )
            sys.exit(2)
        else:
            print(
                (
                    "Default configuration file 'config.json' doesn't exist. "
                    "Continue with default built-in configuration"
                )
            )

    build_theme(configuration)


if __name__ == "__main__":
    main()
