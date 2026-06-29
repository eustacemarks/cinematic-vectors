FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

COPY MovieSearch.sln .
COPY src/MovieSearch.Domain/MovieSearch.Domain.csproj               src/MovieSearch.Domain/
COPY src/MovieSearch.Application/MovieSearch.Application.csproj     src/MovieSearch.Application/
COPY src/MovieSearch.Infrastructure/MovieSearch.Infrastructure.csproj src/MovieSearch.Infrastructure/
COPY src/MovieSearch.Api/MovieSearch.Api.csproj                     src/MovieSearch.Api/
COPY tests/MovieSearch.Tests/MovieSearch.Tests.csproj               tests/MovieSearch.Tests/

RUN dotnet restore src/MovieSearch.Api/MovieSearch.Api.csproj

COPY src/ src/
RUN dotnet publish src/MovieSearch.Api/MovieSearch.Api.csproj \
    -c Release -o /app/publish --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
WORKDIR /app
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "MovieSearch.Api.dll"]