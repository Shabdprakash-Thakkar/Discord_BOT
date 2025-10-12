FROM mcr.microsoft.com/dotnet/sdk:8.0
WORKDIR /src
COPY . .
WORKDIR "/src"
RUN dotnet build "Dashboard.Backend.csproj" -c Release -o /app/build
RUN dotnet publish "Dashboard.Backend.csproj" -c Release -o /app/publish
WORKDIR /app/publish
ENTRYPOINT ["dotnet", "Dashboard.Backend.dll"]