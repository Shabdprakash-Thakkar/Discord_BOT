using Microsoft.EntityFrameworkCore;

namespace Dashboard.Backend.Data
{
    public class ApplicationDbContext : DbContext
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options) : base(options)
        {
        }

        // Add DbSets for your entities here
        // public DbSet<YourEntity> YourEntities { get; set; }
    }
}