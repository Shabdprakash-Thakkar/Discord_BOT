# Stage 1: Build the Blazor WebAssembly app
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY ["Dashboard.Frontend.csproj", "."]
RUN dotnet restore "./Dashboard.Frontend.csproj"
COPY . .
WORKDIR "/src/."
RUN dotnet build "Dashboard.Frontend.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "Dashboard.Frontend.csproj" -c Release -o /app/publish

# Stage 2: Serve the app using Nginx
FROM nginx:alpine AS final
WORKDIR /usr/share/nginx/html
COPY --from=publish /app/publish/wwwroot .
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80