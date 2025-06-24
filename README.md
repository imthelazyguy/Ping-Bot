This updated "manual" explains the powerful new features to anyone visiting your GitHub repository.
# Discord Role Ping & Embed Bot

A powerful, self-hosted Discord bot that pings specified roles at a set time interval using beautiful, custom-built embeds.

## Features

-   **Interactive Embed Builder**: A simple UI with buttons and forms for admins to create, manage, and delete embed templates.
-   **Persistent Storage**: Embed templates are saved per-server and persist through bot restarts.
-   **Custom Pings**: Use your saved embed templates for recurring pings.
-   **Custom Intervals**: Define the ping interval in minutes.
-   **Secure**: Designed for hosting, using environment variables for the bot token.

## How It Works

1.  **Build an Embed**: An admin uses the `!embedbuilder` command to open the menu. They create a new embed template, giving it a name, title, description, and color.
2.  **Set the Ping**: The admin uses the `!setping` command, specifying a role, an interval, and the name of the saved embed template.
3.  **Automated Pinging**: The bot will now ping the specified role in that channel at the set interval, using the custom embed design.

## Commands

### Embed Management

-   `!embedbuilder`
    -   Opens the main interactive menu for managing embeds. Admins can:
        -   **Create New Embed**: Opens a form to design a new embed and save it with a name.
        -   **List My Embeds**: Shows all saved embed templates for the server.
        -   **Delete an Embed**: Provides a dropdown to select and delete an existing template.

### Ping Management

-   `!setping @role <interval_in_minutes> <template_name>`
    -   Starts a recurring ping using a saved embed.
    -   *Example*: `!setping @Announcements 60 weekly-update`
-   `!stopping`
    -   Stops the active pinging schedule for the server.

## Deployment on Runway

1.  **Fork this repository.**
2.  **Create a Bot Application** on the [Discord Developer Portal](https://discord.com/developers/applications) to get your Bot Token.
3.  **Deploy on a Hosting Service (like Runway)**:
    -   Connect your GitHub account.
    -   Select this repository for deployment.
    -   Set the **start command** to: `python main.py`
    -   Go to your project's settings and add an **Environment Variable**:
        -   `KEY`: `BOT_TOKEN`
        -   `VALUE`: `Your_Actual_Discord_Bot_Token_Here`

The bot will start, and you can begin setting up your custom embeds!
