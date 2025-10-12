namespace Dashboard.Backend.Models
{
    public class YouTubeChannel
    {
        public string? yt_channel_id { get; set; }
        public int discord_channel_id { get; set; }
        public int role_id { get; set; }
        public string? yt_channel_name { get; set; }
    }

    public class YouTubeChannelFindResult
    {
        public string? channel_id { get; set; }
        public string? channel_title { get; set; }
        public string? thumbnail_url { get; set; }
    }
}